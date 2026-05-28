# Djabli Nest API Server

Backend VPS untuk sistem **Djabli Nest** — menghubungkan aplikasi mobile pembelian, desktop admin operasional, PostgreSQL, dan penyimpanan file lokal (foto SOP & bukti transfer).

## Arsitektur

```
Djabli Nest Mobile  →  FastAPI (VPS)  →  PostgreSQL + /app/uploads
                            ↑
Djabli Nest Admin   ←  sync REST API
```

**Prinsip bisnis:** batch dari mobile **bukan** stok final. Stok resmi (`inventory_lots`) hanya terbentuk setelah admin melakukan **finalize**.

## Stack

- Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- JWT + bcrypt, PostgreSQL, Docker Compose, Nginx reverse proxy
- Penyimpanan file lokal (bukan BLOB di database)

## Status Batch

| Status | Keterangan |
|--------|------------|
| `DRAFT` | Metadata batch dibuat mobile, belum submit |
| `UPLOADED` | Mobile submit sukses (siap diterima admin) |
| `RECEIVED` | Admin terima di gudang |
| `QUARANTINE` | Isolasi / quarantine |
| `REWEIGHING` | Timbang ulang |
| `REGRADING` | Klasifikasi ulang |
| `FINALIZED` | Stok resmi terbentuk |
| `REJECTED` | Ditolak |
| `CANCELLED` | Dibatalkan |

## Deploy Lokal

```bash
cd djabli_nest_server
cp .env.example .env
# edit SECRET_KEY dan password jika perlu

docker compose up -d --build
```

Cek health:

```bash
curl http://localhost/health
curl http://localhost/api/health/db
```

## Deploy di VPS Ubuntu

1. Install Docker & Docker Compose plugin.
2. Clone project ke `/opt/djabli-nest` (atau folder deploy pilihan Anda).
3. Salin `.env.example` → `.env`, set `SECRET_KEY` kuat, `CORS_ORIGINS`, password DB.
4. `docker compose up -d --build`
5. Buka firewall port 80 (dan 443 setelah SSL).
6. Setup SSL dengan Certbot (lihat bawah).

## Buat Superadmin

Otomatis saat container pertama kali jalan (dari env `INITIAL_SUPERADMIN_*`).

Manual:

```bash
docker compose exec api python -m app.cli create-superadmin
# atau dengan argumen
docker compose exec api python -m app.cli create-superadmin --username superadmin --password 'RahasiaKuat!'
```

Buat user admin/mobile:

```bash
docker compose exec api python -m app.cli create-user \
  --username mobile1 --password secret --full-name "Petugas Lapangan" \
  --role MOBILE_USER --device-id DEVICE-001
docker compose exec api python -m app.cli create-user \
  --username admin1 --password secret --full-name "Admin Gudang" --role ADMIN
```

## Login

**Admin / Desktop:**

```bash
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"SuperAdmin123!"}'
```

**Mobile:**

```bash
curl -X POST http://localhost/api/mobile/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "collector01",
    "password": "...",
    "device_id": "ANDROID-ID-DARI-HP",
    "platform": "android"
  }'
```

`device_id` opsional saat login; jika dikirim, perangkat didaftarkan otomatis ke user tersebut. Saat `POST /api/mobile/batches`, `device_id` yang belum ada juga didaftarkan otomatis (kecuali sudah dipakai user lain → **409**).

Gunakan `access_token` sebagai header: `Authorization: Bearer <token>`.

## Manajemen User (Desktop Admin)

Endpoint prefix: `/api/admin/users` — membutuhkan role **ADMIN** atau **SUPERADMIN**.

### Hak akses role

| Aksi | SUPERADMIN | ADMIN | MOBILE_USER |
|------|------------|-------|-------------|
| Lihat / kelola user | Ya | Ya (MOBILE_USER saja) | Tidak |
| Buat MOBILE_USER | Ya | Ya | Tidak |
| Buat ADMIN / SUPERADMIN | Ya | Tidak | Tidak |
| Reset password | Ya | Ya (target MOBILE_USER) | Tidak |

### Flow Desktop Admin — buat collector mobile

1. Login admin di desktop → dapat JWT.
2. `POST /api/admin/users` dengan role `MOBILE_USER`.
3. Berikan username/password ke petugas lapangan.
4. Petugas login di app mobile (`/api/mobile/auth/login`).
5. `device_id` **otomatis terdaftar** saat login mobile (jika dikirim) atau saat batch pertama dikirim — tidak perlu CLI manual.

### Endpoint

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/admin/users` | Daftar user (`?role=&is_active=&search=`) |
| POST | `/api/admin/users` | Buat user baru |
| GET | `/api/admin/users/{user_id}` | Detail user |
| PATCH | `/api/admin/users/{user_id}` | Update nama / role / aktif |
| POST | `/api/admin/users/{user_id}/reset-password` | Reset password |
| POST | `/api/admin/users/{user_id}/activate` | Aktifkan |
| POST | `/api/admin/users/{user_id}/deactivate` | Nonaktifkan |

Response **tidak** menyertakan `password_hash`.

### Contoh curl — buat MOBILE_USER (superadmin)

```bash
# Login dulu
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"SuperAdmin123!"}'

# Buat collector
curl -X POST http://localhost/api/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "collector01",
    "password": "StrongPassword#123",
    "full_name": "Collector 01",
    "role": "MOBILE_USER",
    "is_active": true
  }'
```

List user dengan filter:

```bash
curl "http://localhost/api/admin/users?role=MOBILE_USER&is_active=true&search=collector" \
  -H "Authorization: Bearer $TOKEN"
```

## Contoh curl — Mobile batch

```bash
TOKEN="..."
curl -X POST http://localhost/api/mobile/batches \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @batch.json
```

Upload foto SOP (4 tipe wajib sebelum submit):

```bash
curl -X POST "http://localhost/api/mobile/batches/{batch_uuid}/photos" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@foto.jpg" \
  -F "file_type=SOP_PHOTO" \
  -F "photo_type=UTUH" \
  -F "sha256=<hex_sha256>"
```

Submit:

```bash
curl -X POST "http://localhost/api/mobile/batches/{batch_uuid}/submit" \
  -H "Authorization: Bearer $TOKEN"
```

## Contoh curl — Admin workflow

```bash
# Sync delta
curl "http://localhost/api/admin/sync/batches?since=2026-05-01T00:00:00Z" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

curl -X POST "http://localhost/api/admin/batches/{uuid}/receive" -H "Authorization: Bearer $ADMIN_TOKEN"
curl -X POST "http://localhost/api/admin/batches/{uuid}/move-to-quarantine" -H "Authorization: Bearer $ADMIN_TOKEN"
# ... reweigh, regrade, finalize
```

Download file (JWT wajib):

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/files/{file_uuid} --output bukti.jpg
```

## Backup & Restore Database

```bash
export DATABASE_URL=postgresql://djabli:djabli_secret@localhost:5432/djablinest
./scripts/backup_postgres.sh
./scripts/restore_postgres.sh ./backups/djablinest_YYYYMMDD.sql.gz
```

## Reset data (keep users)

Untuk mengosongkan semua tabel **kecuali** `users` (dan menjaga `alembic_version`), jalankan:

```bash
cd djabli_nest_server
./scripts/reset_data_keep_users.sh
```

Atau langsung via SQL:

```bash
docker compose exec -T postgres psql -U djabli -d djablinest < ./scripts/reset_data_keep_users.sql
```

Di dalam container:

```bash
docker compose exec -e DATABASE_URL=postgresql://djabli:djabli_secret@postgres:5432/djablinest api \
  sh /app/scripts/backup_postgres.sh
```

## Nginx + SSL (Certbot)

1. Arahkan DNS domain ke IP VPS.
2. Pasang Certbot di host Ubuntu.
3. Uncomment blok `listen 443 ssl` di `nginx/nginx.conf`, sesuaikan `server_name` dan path sertifikat.
4. Reload nginx: `docker compose restart nginx`
5. Redirect HTTP→HTTPS (tambahkan server block redirect di nginx).

Contoh Certbot standalone (hentikan nginx sementara jika perlu):

```bash
sudo certbot certonly --standalone -d api.djablinest.example.com
```

## Flow Mobile → Server → Desktop

1. **Djabli Nest Mobile** login → buat batch (`DRAFT`) + upload 4 foto SOP + submit → `UPLOADED`
2. **Server** simpan metadata, file di `/app/uploads/{year}/{month}/{batch_uuid}/`, sync_version naik
3. **Djabli Nest Admin** sync `GET /api/admin/sync/batches?since=` → receive → quarantine → reweigh → regrade → **finalize**
4. Saat finalize, server membuat `inventory_lots` — ini stok resmi

## Menjalankan Test

```bash
cd djabli_nest_server
pip install -r requirements.txt
set USE_SQLITE_TESTS=1
python -m pytest -v
```

## Struktur Project

Lihat folder `app/` — routes tipis, logic di `services/`, akses DB di `repositories/`.

## Environment Variables

| Variable | Deskripsi |
|----------|-----------|
| `DATABASE_URL` | Connection PostgreSQL |
| `SECRET_KEY` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Masa berlaku token |
| `UPLOAD_DIR` | Folder upload |
| `MAX_UPLOAD_MB` | Batas ukuran file |
| `CORS_ORIGINS` | Daftar origin dipisah koma |
| `INITIAL_SUPERADMIN_*` | Seed superadmin |

## Catatan Keamanan

- Password di-hash bcrypt
- File upload tidak diexpose tanpa JWT (`/api/files/{uuid}`)
- Rate limit sederhana pada login
- Batch `FINALIZED` tidak bisa diedit; koreksi pasca-finalisasi mengembalikan `adjustment not implemented`
