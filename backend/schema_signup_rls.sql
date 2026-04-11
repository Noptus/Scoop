-- Run this in the Supabase SQL Editor to enable direct signup from the frontend.
-- This allows the anon (public) key to insert new users and companies,
-- which is needed because we don't have a hosted backend.

-- Allow anyone to create a user (signup)
CREATE POLICY "Anon can insert users"
  ON users FOR INSERT
  TO anon
  WITH CHECK (true);

-- Allow anyone to insert companies (for their signup)
CREATE POLICY "Anon can insert companies"
  ON companies FOR INSERT
  TO anon
  WITH CHECK (true);
