import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './whatsapp-schema';

declare global {
  // eslint-disable-next-line no-var
  var waClient: postgres.Sql | undefined;
}

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL environment variable is not set');
}

// Reusar conexão em dev (hot reload)
if (!global.waClient) {
  global.waClient = postgres(process.env.DATABASE_URL, { max: 5 });
}

export const waDb = drizzle(global.waClient, { schema });
