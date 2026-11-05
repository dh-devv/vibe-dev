CREATE TABLE app_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  oidc_issuer TEXT NOT NULL,
  oidc_subject TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_app_users_oidc_identity UNIQUE (oidc_issuer, oidc_subject)
);

CREATE TABLE trials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
  case_text TEXT NOT NULL,
  deadline DATE,
  verdict JSONB NOT NULL,
  checks JSONB NOT NULL DEFAULT '[]'::jsonb,
  submitted_at TIMESTAMPTZ NOT NULL,
  accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  first_checked_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_trials_case_length CHECK (char_length(btrim(case_text)) BETWEEN 5 AND 300),
  CONSTRAINT chk_trials_verdict_object CHECK (jsonb_typeof(verdict) = 'object'),
  CONSTRAINT chk_trials_checks_array CHECK (jsonb_typeof(checks) = 'array'),
  CONSTRAINT chk_trials_submitted_before_acceptance CHECK (submitted_at <= accepted_at),
  CONSTRAINT chk_trials_first_check_after_submission CHECK (first_checked_at IS NULL OR first_checked_at >= submitted_at),
  CONSTRAINT chk_trials_completion_after_first_check CHECK (
    completed_at IS NULL OR (first_checked_at IS NOT NULL AND completed_at >= first_checked_at)
  )
);

CREATE INDEX ix_trials_owner_accepted
  ON trials (owner_id, accepted_at DESC);

CREATE FUNCTION set_trials_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_trials_updated_at
BEFORE UPDATE ON trials
FOR EACH ROW
EXECUTE FUNCTION set_trials_updated_at();
