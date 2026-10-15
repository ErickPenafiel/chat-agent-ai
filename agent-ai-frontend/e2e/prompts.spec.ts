import { test, expect } from "@playwright/test"

test.describe("Catálogo de Prompts", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
    await page.getByRole("button", { name: /Prompts del Sistema/i }).click()
    await expect(
      page.getByRole("heading", { name: "Catálogo de Prompts" })
    ).toBeVisible()
  })

  test("debe listar los prompts clave del sistema", async ({ page }) => {
    await expect(page.getByText("agent_chat").first()).toBeVisible()
    await expect(page.getByText("intent_classifier").first()).toBeVisible()
  })

  test("debe permitir previsualizar un prompt con variables dinámicas", async ({
    page,
  }) => {
    // Seleccionar agent_chat
    await page.getByText("agent_chat").first().click()

    // Clic en Previsualizar
    const previewBtn = page.getByRole("button", { name: "Previsualizar" })
    await expect(previewBtn).toBeVisible()
    await previewBtn.click()

    // Debe mostrar la sección de prompt renderizado
    await expect(
      page.getByText(/Prompt Renderizado/i)
    ).toBeVisible({ timeout: 5000 })
    await expect(page.getByText("Lumbre Café").first()).toBeVisible()
  })
})
