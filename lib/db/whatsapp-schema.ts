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

export const contacts = pgTable('contacts', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  waId: text('wa_id').unique().notNull(),
  name: text('name'),
  phone: text('phone'),
  avatarUrl: text('avatar_url'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const conversations = pgTable('conversations', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  contactId: uuid('contact_id')
    .notNull()
    .references(() => contacts.id),
  status: text('status').notNull().default('open'),
  botActive: boolean('bot_active').notNull().default(true),
  unreadCount: integer('unread_count').notNull().default(0),
  lastMessage: text('last_message'),
  lastMessageAt: timestamp('last_message_at'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const messages = pgTable('messages', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  conversationId: uuid('conversation_id')
    .notNull()
    .references(() => conversations.id),
  contactId: uuid('contact_id').references(() => contacts.id),
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

export const mediaFiles = pgTable('media_files', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  messageId: uuid('message_id')
    .notNull()
    .references(() => messages.id),
  waMediaId: text('wa_media_id'),
  url: text('url'),
  mimeType: text('mime_type'),
  filename: text('filename'),
  sizeBytes: integer('size_bytes'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const webhookLogs = pgTable('webhook_logs', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  payload: jsonb('payload'),
  status: text('status').notNull().default('processed'),
  errorMsg: text('error_msg'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Relations
export const contactsRelations = relations(contacts, ({ many }) => ({
  conversations: many(conversations),
  messages: many(messages),
}));

export const conversationsRelations = relations(
  conversations,
  ({ one, many }) => ({
    contact: one(contacts, {
      fields: [conversations.contactId],
      references: [contacts.id],
    }),
    messages: many(messages),
  })
);

export const messagesRelations = relations(messages, ({ one, many }) => ({
  conversation: one(conversations, {
    fields: [messages.conversationId],
    references: [conversations.id],
  }),
  contact: one(contacts, {
    fields: [messages.contactId],
    references: [contacts.id],
  }),
  mediaFiles: many(mediaFiles),
}));

export const mediaFilesRelations = relations(mediaFiles, ({ one }) => ({
  message: one(messages, {
    fields: [mediaFiles.messageId],
    references: [messages.id],
  }),
}));

// Types
export type Contact = typeof contacts.$inferSelect;
export type NewContact = typeof contacts.$inferInsert;
export type Conversation = typeof conversations.$inferSelect;
export type NewConversation = typeof conversations.$inferInsert;
export type Message = typeof messages.$inferSelect;
export type NewMessage = typeof messages.$inferInsert;
export type MediaFile = typeof mediaFiles.$inferSelect;
export type WebhookLog = typeof webhookLogs.$inferSelect;

export type ConversationWithContact = Conversation & {
  contact: Contact;
};

export type MessageWithMedia = Message & {
  mediaFiles: MediaFile[];
};
