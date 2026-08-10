-- Remove seeded channel messages.
DELETE FROM messages WHERE channel_id IN ('general', 'frontend') AND author_id IS NULL;
