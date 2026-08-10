# PostgreSQL Setup

Set DATABASE_URL in SocialHub/.env:

`env
DATABASE_URL=postgresql://user:password@host:5432/socialhub
DATABASE_URL_ASYNC=postgresql+asyncpg://user:password@host:5432/socialhub
`

Then run:

`ash
cd backend
python -m alembic upgrade head
`

Do not use create_all as a production migration substitute.
