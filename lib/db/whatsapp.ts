import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './whatsapp-schema';

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL environment variable is not set');
}

const client = postgres(process.env.DATABASE_URL, {
  max: 1,        // serverless: uma conexão por invocação
  prepare: false, // obrigatório para Supabase connection pooler
});

export const waDb = drizzle(client, { schema });
