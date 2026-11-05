targetScope = 'subscription'

@minLength(1)
@maxLength(30)
@description('azd 환경 이름. 리소스 이름과 태그에 쓴다')
param environmentName string

@minLength(1)
param location string

@secure()
@description('Copilot Requests 권한을 준 fine-grained PAT')
param copilotGithubToken string

@secure()
@description('PostgreSQL 관리자 비밀번호. URL에 쓰이므로 영문·숫자만 쓴다')
param postgresPassword string

@secure()
@description('세션 서명 키. 32자 이상')
param sessionSecretKey string

param oidcIssuer string = ''
param oidcClientId string = ''
@secure()
param oidcClientSecret string = ''

param copilotModel string = ''

var tags = { 'azd-env-name': environmentName }

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    copilotGithubToken: copilotGithubToken
    postgresPassword: postgresPassword
    sessionSecretKey: sessionSecretKey
    oidcIssuer: oidcIssuer
    oidcClientId: oidcClientId
    oidcClientSecret: oidcClientSecret
    copilotModel: copilotModel
  }
}

output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.registryEndpoint
output SERVICE_WEB_URI string = resources.outputs.appUrl
