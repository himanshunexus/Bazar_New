# Supabase Setup for BAZAR

BAZAR uses Supabase only as plain PostgreSQL plus PostGIS. Do not enable Supabase Auth for this app.

1. Create a Supabase project.
2. In Database settings, copy the pooler connection string.
3. Put that string in `DATABASE_URL`.
4. If using transaction-mode pooling on port `6543`, set `DISABLE_SERVER_SIDE_CURSORS=True`.
5. Set `DB_SSL_REQUIRE=True` for hosted Supabase.
6. Run migrations:

```bash
python manage.py migrate
```

7. Optional: paste `db/extras.sql` into the Supabase SQL editor. It is idempotent and can be run more than once.
8. Run the lock-down command:

```bash
python manage.py lockdown_db
```

9. Seed demo data and verify nearby search:

```bash
python manage.py seed_demo
python manage.py shell -c "from apps.shops.models import Shop; print([(s.name, getattr(s, 'distance_m', None)) for s in Shop.objects.nearby(28.6139,77.2090,5)])"
```

Verification queries:

```sql
select extname from pg_extension where extname = 'postgis';
select tgname from pg_trigger where tgname = 'trg_set_shop_location';
select * from get_shops_within_radius(28.6139, 77.2090, 5);
select relname, relrowsecurity
from pg_class
join pg_namespace on pg_namespace.oid = pg_class.relnamespace
where nspname = 'public' and relkind = 'r';
```
## Persistent demo data

From a trusted machine, configure `DATABASE_URL` with the Supabase transaction-pooler URL and run:

```bash
python manage.py migrate
python manage.py seed_production --confirm
```

Useful variables are `DEFAULT_LAT`, `DEFAULT_LNG`, `SEED_CITY`, `SEED_PINCODE`, and `SEED_DEMO_PASSWORD`. Set `SEED_ON_DEPLOY=true` only if Render should run the idempotent seed during deployment. `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` configure the optional admin command.

To inspect the seeded records in Supabase:

```sql
select 'users' as table_name, count(*) from accounts_user where username like 'demo_%'
union all select 'shops', count(*) from shops_shop where slug like 'demo-%'
union all select 'products', count(*) from products_product where slug like 'demo-%'
union all select 'orders', count(*) from cart_order where order_number like 'DEMO-%';

select * from get_shops_within_radius(28.6139, 77.2090, 5);
```

To remove only demo data and recreate it:

```bash
python manage.py seed_production --wipe-demo --confirm
```
