import type { Config } from 'drizzle-kit';
import dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

export default {
  schema: './lib/db/whatsapp-schema.ts',
  out: './lib/db/whatsapp-migrations',
  dialect: 'postgresql',
  dbCredentials: {
    url:
      process.env.WHATSAPP_DATABASE_URL ||
      process.env.POSTGRES_URL ||
      '',
  },
} satisfies Config;
