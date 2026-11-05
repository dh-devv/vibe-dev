targetScope = 'resourceGroup'

param environmentName string
param location string
param tags object

@secure()
param copilotGithubToken string
@secure()
param postgresPassword string
@secure()
param sessionSecretKey string
param oidcIssuer string
param oidcClientId string
@secure()
param oidcClientSecret string
param copilotModel string

var token = toLower(uniqueString(subscription().id, environmentName))
var appName = 'ca-${take(environmentName, 20)}-${take(token, 6)}'
var dbAdmin = 'vibeadmin'
var dbName = 'vibe_dev'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${token}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'cr${token}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${token}'
  location: location
  tags: tags
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, 'acrpull')
  scope: registry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: 'psql-${token}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: dbAdmin
    administratorLoginPassword: postgresPassword
    storage: { storageSizeGB: 32 }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: { mode: 'Disabled' }
    network: { publicNetworkAccess: 'Enabled' }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: dbName
}

// 0.0.0.0 규칙은 Azure 서비스에서 오는 연결만 허용한다
resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${token}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

var hasOidc = !empty(oidcIssuer) && !empty(oidcClientId) && !empty(oidcClientSecret)

var baseSecrets = [
  { name: 'copilot-github-token', value: copilotGithubToken }
  { name: 'database-url', value: 'postgresql://${dbAdmin}:${postgresPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${dbName}?sslmode=require' }
  { name: 'session-secret-key', value: sessionSecretKey }
]
var oidcSecrets = hasOidc ? [{ name: 'oidc-client-secret', value: oidcClientSecret }] : []

var baseEnv = [
  { name: 'COPILOT_GITHUB_TOKEN', secretRef: 'copilot-github-token' }
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'SESSION_SECRET_KEY', secretRef: 'session-secret-key' }
  { name: 'PUBLIC_BASE_URL', value: 'https://${appName}.${env.properties.defaultDomain}' }
  { name: 'RUN_MIGRATIONS', value: 'true' }
  { name: 'COOKIE_SECURE', value: 'true' }
]
var oidcEnv = hasOidc ? [
  { name: 'OIDC_ISSUER', value: oidcIssuer }
  { name: 'OIDC_CLIENT_ID', value: oidcClientId }
  { name: 'OIDC_CLIENT_SECRET', secretRef: 'oidc-client-secret' }
] : []
var modelEnv = empty(copilotModel) ? [] : [{ name: 'COPILOT_MODEL', value: copilotModel }]

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  dependsOn: [acrPull, database, allowAzure]
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: identity.id
        }
      ]
      secrets: concat(baseSecrets, oidcSecrets)
    }
    template: {
      containers: [
        {
          name: 'web'
          // azd deploy가 빌드한 이미지로 교체한다
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat(baseEnv, oidcEnv, modelEnv)
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output registryEndpoint string = registry.properties.loginServer
output appUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
