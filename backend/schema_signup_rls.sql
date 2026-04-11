-- Scoop - Signup RLS and RPC
-- Run this in the Supabase SQL Editor to enable direct signup from the frontend.
-- The signup() function runs as SECURITY DEFINER (bypasses RLS) so the anon
-- role can create users without needing direct INSERT policies.

-- Signup RPC function (called by frontend JS via /rest/v1/rpc/signup)
CREATE OR REPLACE FUNCTION public.signup(p_email text, p_product text, p_companies text[])
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_user_id uuid;
  v_company text;
BEGIN
  INSERT INTO users (email, product)
  VALUES (p_email, p_product)
  ON CONFLICT (email) DO NOTHING
  RETURNING id INTO v_user_id;

  IF v_user_id IS NULL THEN
    RETURN json_build_object('status', 'exists');
  END IF;

  FOREACH v_company IN ARRAY p_companies LOOP
    INSERT INTO companies (user_id, name) VALUES (v_user_id, v_company);
  END LOOP;

  RETURN json_build_object('status', 'ok', 'id', v_user_id);
END;
$$;

GRANT EXECUTE ON FUNCTION public.signup TO anon;

NOTIFY pgrst, 'reload schema';
