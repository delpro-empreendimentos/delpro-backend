DEFAULT_KEYS = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
    "API_KEY": "test",
    "PROJECT_ID": "test",
    "GEMINI_MODEL": "gemini-2.5-flash",
    "MAX_TOKENS": "1024",
    "LLM_TEMPERATURE": "0",
    "MAX_HISTORY_MESSAGES": "20",
    "LOG_LEVEL": "INFO",
    "MAX_TOKENS_SUMMARY": "1",
    # RAG Configuration
    "EMBEDDING_MODEL": "models/gemini-embedding-001",
    "CHUNK_SIZE": "500",
    "CHUNK_OVERLAP": "100",
    "RAG_TOP_K": "1",
    # WhatsApp Configuration
    "WHATSAPP_ACCESS_TOKEN": "test-token",
    "WHATSAPP_PHONE_NUMBER_ID": "test-phone-id",
    "WHATSAPP_VERIFY_TOKEN": "test-verify-token",
    "WHATSAPP_APP_SECRET": "test-app-secret",
    "WHATSAPP_API_VERSION": "v21.0",
    "WHATSAPP_RECIPIENT_WAID": "test-recipient",
}
