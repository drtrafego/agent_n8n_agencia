import {
  pgTable,
  uuid,
  text,
  boolean,
  integer,
  timestamp,
  jsonb,
} from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';
import { sql } from 'drizzle-orm';

// Prefixo wa_ para separar das tabelas de auth no mesmo banco
export const waContacts = pgTable('wa_contacts', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  waId: text('wa_id').unique().notNull(),
  name: text('name'),
  phone: text('phone'),
  avatarUrl: text('avatar_url'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const waConversations = pgTable('wa_conversations', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  contactId: uuid('contact_id')
    .notNull()
    .references(() => waContacts.id),
  status: text('status').notNull().default('open'),
  botActive: boolean('bot_active').notNull().default(true),
  unreadCount: integer('unread_count').notNull().default(0),
  lastMessage: text('last_message'),
  lastMessageAt: timestamp('last_message_at'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const waMessages = pgTable('wa_messages', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  conversationId: uuid('conversation_id')
    .notNull()
    .references(() => waConversations.id),
  contactId: uuid('contact_id').references(() => waContacts.id),
  waMessageId: text('wa_message_id').unique(),
  direction: text('direction').notNull(),
  type: text('type').notNull(),
  body: text('body'),
  mediaUrl: text('media_url'),
  mediaMimeType: text('media_mime_type'),
  mediaFilename: text('media_filename'),
  status: text('status').notNull().default('received'),
  sentBy: text('sent_by'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const waMediaFiles = pgTable('wa_media_files', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  messageId: uuid('message_id')
    .notNull()
    .references(() => waMessages.id),
  waMediaId: text('wa_media_id'),
  url: text('url'),
  mimeType: text('mime_type'),
  filename: text('filename'),
  sizeBytes: integer('size_bytes'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const waWebhookLogs = pgTable('wa_webhook_logs', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  payload: jsonb('payload'),
  status: text('status').notNull().default('processed'),
  errorMsg: text('error_msg'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Relations
export const waContactsRelations = relations(waContacts, ({ many }) => ({
  conversations: many(waConversations),
  messages: many(waMessages),
}));

export const waConversationsRelations = relations(
  waConversations,
  ({ one, many }) => ({
    contact: one(waContacts, {
      fields: [waConversations.contactId],
      references: [waContacts.id],
    }),
    messages: many(waMessages),
  })
);

export const waMessagesRelations = relations(waMessages, ({ one, many }) => ({
  conversation: one(waConversations, {
    fields: [waMessages.conversationId],
    references: [waConversations.id],
  }),
  contact: one(waContacts, {
    fields: [waMessages.contactId],
    references: [waContacts.id],
  }),
  mediaFiles: many(waMediaFiles),
}));

export const waMediaFilesRelations = relations(waMediaFiles, ({ one }) => ({
  message: one(waMessages, {
    fields: [waMediaFiles.messageId],
    references: [waMessages.id],
  }),
}));

// Types
export type Contact = typeof waContacts.$inferSelect;
export type NewContact = typeof waContacts.$inferInsert;
export type Conversation = typeof waConversations.$inferSelect;
export type NewConversation = typeof waConversations.$inferInsert;
export type Message = typeof waMessages.$inferSelect;
export type NewMessage = typeof waMessages.$inferInsert;
export type MediaFile = typeof waMediaFiles.$inferSelect;
export type WebhookLog = typeof waWebhookLogs.$inferSelect;

export type ConversationWithContact = Conversation & {
  contact: Contact;
};

export type MessageWithMedia = Message & {
  mediaFiles: MediaFile[];
};
