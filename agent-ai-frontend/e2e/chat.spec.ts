import { test, expect } from "@playwright/test"

test.describe("Simulador de Chat en Vivo", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
    // Navegar a Simulador de Chat desde el sidebar
    await page
      .getByRole("button", { name: "Simulador de Chat En vivo" })
      .click()
    await expect(
      page.getByRole("heading", { name: "Simulador de Chat en Vivo" })
    ).toBeVisible()
  })

  test("debe mostrar el mensaje de bienvenida inicial", async ({ page }) => {
    await expect(
      page.getByText(/¡Hola! Bienvenido a Lumbre Café/i)
    ).toBeVisible()
    await expect(page.getByText("Inspector de Grafo LangGraph")).toBeVisible()
  })

  test("debe enviar consulta usando un chip de sugerencia rápida y recibir respuesta", async ({
    page,
  }) => {
    // Hacer clic en sugerencia "¿Qué café venden?"
    const suggestion = page.getByRole("button", { name: "¿Qué café venden?" })
    await expect(suggestion).toBeVisible()
    await suggestion.click()

    // Comprobar que el mensaje del usuario aparece en la burbuja de chat
    const userBubble = page.getByRole("paragraph").filter({ hasText: "¿Qué café venden?" })
    await expect(userBubble).toBeVisible()

    // Esperar respuesta del agente
    const agentBubble = page.locator(".rounded-tl-xs").first()
    await expect(agentBubble).toBeVisible({ timeout: 10000 })
  })

  test("debe detectar intención de escalado cuando el usuario solicita una persona", async ({
    page,
  }) => {
    const input = page.getByPlaceholder("Escribe una pregunta para el agente...")
    await input.fill("Quiero hablar con una persona por favor")
    await page.keyboard.press("Enter")

    // Verificar mensaje de usuario
    const userBubble = page.getByRole("paragraph").filter({ hasText: "Quiero hablar con una persona" })
    await expect(userBubble).toBeVisible()

    // Esperar respuesta y badge de Escalado
    await expect(page.getByText("Escalado").first()).toBeVisible({ timeout: 10000 })
  })

  test("debe permitir reiniciar la conversación", async ({ page }) => {
    const input = page.getByPlaceholder("Escribe una pregunta para el agente...")
    await input.fill("Mensaje de prueba temporal")
    await page.keyboard.press("Enter")
    await expect(page.getByText("Mensaje de prueba temporal")).toBeVisible()

    // Clic en reiniciar
    await page.getByRole("button", { name: "Reiniciar" }).click()
    await expect(page.getByText("Mensaje de prueba temporal")).not.toBeVisible()
    await expect(
      page.getByText(/¡Hola! Bienvenido a Lumbre Café/i)
    ).toBeVisible()
  })
})
