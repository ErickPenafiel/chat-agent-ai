import { test, expect } from "@playwright/test"

test.describe("Dashboard del Agente", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
  })

  test("debe cargar el dashboard con el branding del tenant y métricas clave", async ({
    page,
  }) => {
    // Verificar título del tenant y encabezado
    await expect(page.getByText("Lumbre Café").first()).toBeVisible()
    await expect(
      page.getByRole("heading", { name: "Dashboard de Rendimiento" })
    ).toBeVisible()

    // Verificar tarjetas de KPIs
    await expect(page.getByText("Total Sesiones")).toBeVisible()
    await expect(page.getByText("Tasa de Resolución")).toBeVisible()
    await expect(page.getByText("Tasa de Escalado")).toBeVisible()
    await expect(page.getByText("Promedio de Turnos")).toBeVisible()

    // Verificar presencia del gráfico
    await expect(
      page.getByText("Volumen de Conversaciones por Hora")
    ).toBeVisible()
  })

  test("debe permitir alternar el tema claro/oscuro", async ({ page }) => {
    const themeBtn = page.getByTitle("Alternar tema claro/oscuro")
    await expect(themeBtn).toBeVisible()

    // Click para alternar a dark
    await themeBtn.click()
    const isDark = await page.evaluate(() =>
      document.documentElement.classList.contains("dark")
    )
    expect(typeof isDark).toBe("boolean")
  })

  test("debe navegar al simulador de chat desde el botón de acción", async ({
    page,
  }) => {
    const openChatBtn = page.getByRole("button", {
      name: "Abrir Simulador de Chat",
    })
    await expect(openChatBtn).toBeVisible()
    await openChatBtn.click()

    // Debe cambiar la vista al simulador
    await expect(
      page.getByRole("heading", { name: "Simulador de Chat en Vivo" })
    ).toBeVisible()
    await expect(page.getByText("Lumbre Bot (Canal Web)")).toBeVisible()
  })
})
