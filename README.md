# 🛒 Ecommerce Multitenant — Backend Microservicios

Backend completo para ecommerce multitenant construido con **FastAPI**, arquitectura **hexagonal + event-driven**, persistencia poliglota (**PostgreSQL + MongoDB**), **RabbitMQ**, **Redis**, **Docker** y **Kubernetes**.

---

## 📐 Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx API Gateway                      │
│              (Rate limiting + Routing)                    │
└───────────┬──────┬──────┬──────┬──────┬──────┬──────────┘
            │      │      │      │      │      │
          auth   users  camp. prod. orders deliv. notif.
            │      │      │      │      │      │      │
            └──────┴──────┴──┬───┴──────┴──────┴──────┘
                             │
              ┌──────────────┼──────────────┐
           Postgres       MongoDB         Redis
        (transaccional)   (logs/audit)   (cache)
              │
           RabbitMQ
        (eventos dominio)
```

### Patrón Hexagonal por servicio
```
src/
├── domain/              ← Entidades, puertos (interfaces)
│   ├── entities/        ← Lógica de negocio pura
│   └── ports/           ← Contratos/interfaces
├── application/         ← Casos de uso, DTOs
│   ├── use_cases/
│   └── dtos/
└── infrastructure/      ← Adaptadores concretos
    ├── adapters/
    │   ├── postgres/    ← SQLAlchemy async
    │   ├── mongo/       ← Motor async
    │   ├── redis/       ← Cache
    │   └── rabbitmq/    ← Publisher/Consumer
    └── api/
        └── routes/      ← FastAPI routers
```

---

## 🗂 Servicios (7 microservicios)

| Servicio | Puerto | BD Principal | BD Logs | Descripción |
|---|---|---|---|---|
| **auth** | 8001 | Postgres | - | JWT + OAuth2 Google |
| **users** | 8002 | Postgres | MongoDB | Admins, Proveedores, Clientes |
| **campaigns** | 8003 | Postgres | MongoDB | Orquestador central (diamante) |
| **products** | 8004 | Postgres | - | Productos, Servicios, Sin Receta |
| **orders** | 8005 | Postgres | - | Órdenes + Ventas (transaccional) |
| **deliveries** | 8006 | Postgres | MongoDB | Motorizado, QR de entrega |
| **notifications** | 8007 | - | MongoDB | Email + QR por eventos |

---

## 🔄 Flujo de Eventos (RabbitMQ)

```
[Cliente] → POST /orders
    │
    └─► order.created ──► [deliveries] crea entrega pendiente
                         [notifications] confirma recepción

[Admin] → POST /orders/{id}/pay
    │
    └─► order.paid ──► [campaigns] incrementa contador cupón
                      [deliveries] auto-crea entrega
                      [notifications] envía email confirmación

[Motorizado] → PATCH /deliveries/{id}/complete
    │
    └─► delivery.completed ──► [notifications] envía email + QR PNG

[Admin] → POST /campaigns
    │
    └─► campaign.created ──► [orders] registra campañas activas

[Admin] → PATCH /campaigns/{id}/activate
    │
    └─► campaign.activated ──► [orders] habilita cupón para checkout
```

---

## 🗄 Persistencia Poliglota

### PostgreSQL (datos transaccionales)
- `auth.auth_users` — credenciales y roles
- `users.user_profiles` — perfiles de usuarios
- `campaigns.campaigns` — campañas, cupones, extras
- `products.products` — catálogo con stock
- `orders.orders` — órdenes de compra
- `orders.sales` — registro de ventas (accounting)
- `deliveries.deliveries` — entregas y QR

### MongoDB (logs no-transaccionales)
- `ecommerce_logs.campaign_logs` — auditoría de campañas
- `ecommerce_logs.notification_logs` — historial de emails enviados
- `ecommerce_logs.delivery_logs` — trazabilidad de entregas

### Redis (caché)
- Tokens de refresco JWT (TTL = 7 días)
- Caché de productos por tenant (TTL = 5 min)
- Sesiones activas

---

## 🚀 Inicio Rápido

### 1. Clonar y configurar
```bash
git clone <repo>
cd ecommerce-multitenant
cp .env.example .env
# Editar .env con tus valores reales
```

### 2. Levantar todo con Docker Compose
```bash
docker-compose up -d

# Verificar servicios
docker-compose ps
curl http://localhost/health
```

### 3. Verificar servicios individuales
```bash
curl http://localhost:8001/health   # auth
curl http://localhost:8002/health   # users
curl http://localhost:8003/health   # campaigns
curl http://localhost:8004/health   # products
curl http://localhost:8005/health   # orders
curl http://localhost:8006/health   # deliveries
curl http://localhost:8007/health   # notifications
```

---

## 🔐 Autenticación

### Registro de usuario
```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-demo-001",
    "email": "admin@farmacia.ec",
    "password": "Password123!",
    "roles": ["admin"]
  }'
```

### Login
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-demo-001",
    "email": "admin@farmacia.ec",
    "password": "Password123!"
  }'
# Respuesta: { "access_token": "...", "refresh_token": "...", "expires_in": 1800 }
```

### Usar el token
```bash
export TOKEN="eyJ..."
curl -H "Authorization: Bearer $TOKEN" http://localhost:8004/api/v1/products/
```

---

## 📦 Flujo de Negocio Completo

### 1. Crear proveedor
```bash
curl -X POST http://localhost:8002/api/v1/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"auth_user_id":"<id>","user_type":"provider","first_name":"Juan","last_name":"Pérez","email":"juan@farmacia.ec","company_name":"Farmacia Central","ruc":"0190123456001"}'
```

### 2. Crear producto
```bash
curl -X POST http://localhost:8004/api/v1/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Paracetamol 500mg","description":"Analgésico","product_type":"product","sku":"PARA-500","price":2.50,"stock":100,"requires_prescription":false}'
```

### 3. Crear campaña con cupón
```bash
curl -X POST http://localhost:8003/api/v1/campaigns/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Promo Diciembre","description":"20% en genéricos","discount_type":"percentage","discount_value":20,"product_ids":["<product_id>"],"service_ids":[],"start_date":"2025-12-01T00:00:00","end_date":"2025-12-31T23:59:59","coupon_code":"DIC20","max_uses":200,"extra":{"tiempo_horas":720,"minimo_vender":10.0,"maximo_vender":500.0}}'
```

### 4. Validar cupón
```bash
curl "http://localhost:8003/api/v1/campaigns/validate-coupon?code=DIC20&base_price=50.0" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Crear orden
```bash
curl -X POST http://localhost:8005/api/v1/orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"items":[{"product_id":"<id>","product_name":"Paracetamol 500mg","quantity":2,"unit_price":2.50}],"delivery_address":"Av. Solano 123, Cuenca","coupon_code":"DIC20"}'
```

### 6. Pagar orden
```bash
curl -X POST http://localhost:8005/api/v1/orders/<order_id>/pay \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"payment_method":"card","payment_reference":"VISA-1234-5678"}'
# ► Dispara order.paid → crea entrega + envía email
```

### 7. Asignar motorizado
```bash
curl -X PATCH http://localhost:8006/api/v1/deliveries/<delivery_id>/assign \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"motorizado_id":"moto-001"}'
```

### 8. Completar entrega (genera QR)
```bash
curl -X PATCH http://localhost:8006/api/v1/deliveries/<delivery_id>/complete \
  -H "Authorization: Bearer $TOKEN"
# ► Genera QR PNG base64 + dispara delivery.completed → envía email con QR
```

---

## 🧪 Tests

```bash
# Auth service
cd services/auth && pytest tests/ -v

# Orders service
cd services/orders && pytest tests/ -v

# Campaigns service
cd services/campaigns && pytest tests/ -v

# Deliveries service
cd services/deliveries && pytest tests/ -v
```

---

## ☸️ Kubernetes

```bash
# Staging
kubectl apply -k infrastructure/k8s/overlays/dev

# Producción
kubectl apply -k infrastructure/k8s/overlays/prod

# Ver pods
kubectl get pods -n ecommerce-prod

# Ver logs de orders
kubectl logs -f deployment/orders-service -n ecommerce-prod
```

---

## 📊 Monitoreo

- **RabbitMQ Management**: http://localhost:15672 (admin/secret)
- **Docs Auth**: http://localhost:8001/docs
- **Docs Orders**: http://localhost:8005/docs
- **Docs Campaigns**: http://localhost:8003/docs

---

## 🏗 Tecnologías

| Tecnología | Uso |
|---|---|
| FastAPI | Framework async HTTP |
| SQLAlchemy 2 async | ORM Postgres |
| Motor | Driver async MongoDB |
| aio-pika | Cliente RabbitMQ async |
| redis-py async | Cache y tokens |
| PyJWT + bcrypt | Autenticación |
| Authlib | OAuth2 Google |
| qrcode + Pillow | Generación QR PNG |
| Alembic | Migraciones Postgres |
| Docker + Compose | Contenedores desarrollo |
| Kubernetes + Kustomize | Orquestación producción |
| GitHub Actions | CI/CD pipeline |
