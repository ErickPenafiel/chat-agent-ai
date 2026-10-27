# Política de seguridad

Si encuentras una vulnerabilidad, **no abras un issue público**. Repórtala en
privado desde la pestaña *Security → Report a vulnerability* de este repositorio.

Nunca subas claves reales (`.env`, credenciales de Firebase, tokens de WhatsApp
o de proveedores LLM). Solo se versionan los archivos `.env.example`.
`auth.mode: disabled` es únicamente para desarrollo local.
