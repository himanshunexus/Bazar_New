CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
ALTER TABLE shops_shop ADD COLUMN IF NOT EXISTS location extensions.geography(Point,4326);

CREATE OR REPLACE FUNCTION public.set_shop_location()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
    IF NEW.latitude IS NULL OR NEW.longitude IS NULL THEN
        NEW.location = NULL;
    ELSE
        NEW.location = extensions.ST_SetSRID(extensions.ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::extensions.geography;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_set_shop_location ON shops_shop;
CREATE TRIGGER trg_set_shop_location
BEFORE INSERT OR UPDATE OF latitude, longitude ON shops_shop
FOR EACH ROW EXECUTE FUNCTION public.set_shop_location();

UPDATE shops_shop
SET location = extensions.ST_SetSRID(extensions.ST_MakePoint(longitude, latitude), 4326)::extensions.geography
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_shops_location ON shops_shop USING GIST (location);

CREATE OR REPLACE FUNCTION public.get_shops_within_radius(
    user_lat double precision,
    user_lng double precision,
    radius_km double precision DEFAULT 5.0
)
RETURNS TABLE(shop_id bigint, distance_meters double precision)
LANGUAGE sql
STABLE
SET search_path = public, extensions
AS $$
    SELECT s.id,
           extensions.ST_Distance(
               s.location,
               extensions.ST_SetSRID(extensions.ST_MakePoint(user_lng, user_lat), 4326)::extensions.geography
           ) AS distance_meters
    FROM shops_shop s
    WHERE s.is_active = true
      AND s.location IS NOT NULL
      AND extensions.ST_DWithin(
          s.location,
          extensions.ST_SetSRID(extensions.ST_MakePoint(user_lng, user_lat), 4326)::extensions.geography,
          radius_km * 1000
      )
    ORDER BY distance_meters ASC;
$$;
