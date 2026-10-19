-- Local disposable restore only, inside the import transaction.
-- pg_dump ACLs assume PostgreSQL's canonical creation privileges. Supabase's
-- self-hosted template may instead grant ALL to anon/authenticated by default.
-- Reset the importing role and postgres (the LingoFlow object owner): identity
-- sequences are created as the table owner even when another admin imports.
-- Existing objects and RLS are untouched.
-- The archive subsequently restores its own default-privilege statements.
DO $restore_defaults$
DECLARE
  item record;
  object_kind text;
  creator text;
BEGIN
  FOR creator IN
    SELECT rolname FROM pg_roles WHERE rolname IN (current_user, 'postgres')
  LOOP
    FOR item IN
      SELECT DISTINCT d.defaclnamespace, n.nspname, d.defaclobjtype,
             a.grantee, r.rolname
      FROM pg_default_acl d
      LEFT JOIN pg_namespace n ON n.oid = d.defaclnamespace
      CROSS JOIN LATERAL aclexplode(d.defaclacl) a
      LEFT JOIN pg_roles r ON r.oid = a.grantee
      WHERE d.defaclrole = (SELECT oid FROM pg_roles WHERE rolname = creator)
    LOOP
      object_kind := CASE item.defaclobjtype
        WHEN 'r' THEN 'TABLES' WHEN 'S' THEN 'SEQUENCES'
        WHEN 'f' THEN 'FUNCTIONS' WHEN 'T' THEN 'TYPES'
        WHEN 'n' THEN 'SCHEMAS' END;
      IF object_kind IS NULL THEN
        RAISE EXCEPTION 'Unsupported local default privilege object type';
      END IF;
      EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I%s REVOKE ALL ON %s FROM %s',
        creator,
        CASE WHEN item.defaclnamespace = 0 THEN '' ELSE format(' IN SCHEMA %I', item.nspname) END,
        object_kind,
        CASE WHEN item.grantee = 0 THEN 'PUBLIC' ELSE format('%I', item.rolname) END);
    END LOOP;
    FOREACH object_kind IN ARRAY ARRAY['TABLES', 'SEQUENCES', 'FUNCTIONS', 'TYPES', 'SCHEMAS']
    LOOP
      EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I GRANT ALL ON %s TO %I',
        creator, object_kind, creator);
    END LOOP;
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I GRANT EXECUTE ON FUNCTIONS TO PUBLIC', creator);
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I GRANT USAGE ON TYPES TO PUBLIC', creator);
  END LOOP;
END
$restore_defaults$;
