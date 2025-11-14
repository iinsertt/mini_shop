This is a test project. Production use is permitted.  
You'll need to create a `.env` file and supply the necessary data.  
Run via Docker Compose only.

**.env example:**

```env
TG_API_TOKEN=TOKEN_FROM_BOTFATHER

POSTGRES_USER=testuser        <-- On first boot a user with this data will be created
POSTGRES_PASSWORD=testpass    <--
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=testdb

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

LOG_LEVEL=INFO
