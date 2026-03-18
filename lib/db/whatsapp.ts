import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './whatsapp-schema';

declare global {
  // eslint-disable-next-line no-var
  var waClient: postgres.Sql | undefined;
}

const connectionString =
  process.env.WHATSAPP_DATABASE_URL ||
  process.env.POSTGRES_URL ||
  '';

if (!connectionString) {
  throw new Error(
    'WHATSAPP_DATABASE_URL or POSTGRES_URL environment variable is not set'
  );
}

// Reusar conexão em dev (hot reload)
if (!global.waClient) {
  global.waClient = postgres(connectionString, { max: 5 });
}

export const waDb = drizzle(global.waClient, { schema });
