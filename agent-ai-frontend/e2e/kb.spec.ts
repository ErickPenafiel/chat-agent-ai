import { test, expect } from "@playwright/test"

test.describe("Base de Conocimiento (KB)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
    await page.getByRole("button", { name: /Base de Conocimiento/i }).click()
    await expect(
      page.getByRole("heading", { name: "Base de Conocimiento" })
    ).toBeVisible()
  })

  test("debe mostrar los bloques de la base de conocimiento", async ({
    page,
  }) => {
    await expect(page.getByText("Qué vende Lumbre Café").first()).toBeVisible()
    await expect(page.getByText("Precios").first()).toBeVisible()
    await expect(page.getByText("Suscripción mensual").first()).toBeVisible()
  })

  test("debe filtrar bloques mediante el buscador de texto", async ({
    page,
  }) => {
    const searchInput = page.getByPlaceholder(/Buscar por título/i)
    await searchInput.fill("suscripción")

    // El bloque de suscripción debe permanecer visible
    await expect(page.getByText("Suscripción mensual").first()).toBeVisible()

    // Bloques no relacionados no deben mostrarse
    await expect(page.getByText("Tiempos y costos de envío")).not.toBeVisible()
  })

  test("debe permitir abrir y cerrar el modal con detalles del bloque", async ({
    page,
  }) => {
    // Abrir bloque de suscripción
    const blockCard = page.getByText("Suscripción mensual").first()
    await blockCard.click()

    // Verificar modal abierto con contenido semántico y preguntas de ejemplo
    await expect(page.getByText("Contenido Semántico:")).toBeVisible()
    await expect(
      page.getByText(/La suscripción envía una bolsa/i).first()
    ).toBeVisible()

    // Cerrar modal
    const closeBtn = page.getByRole("button", { name: "Cerrar" })
    await closeBtn.click()
    await expect(page.getByText("Contenido Semántico:")).not.toBeVisible()
  })

  test("debe permitir abrir el formulario y crear un nuevo bloque de conocimiento", async ({
    page,
  }) => {
    // Clic en "Nuevo Bloque"
    const newBlockBtn = page.getByRole("button", { name: "Nuevo Bloque" })
    await expect(newBlockBtn).toBeVisible()
    await newBlockBtn.click()

    // Verificar modal abierto
    await expect(
      page.getByRole("heading", { name: "Nuevo Bloque de Conocimiento" })
    ).toBeVisible()

    // Llenar formulario
    const titleInput = page.getByPlaceholder("Ej. Métodos de Pago Aceptados")
    await titleInput.fill("Políticas de Garantía y Reembolso")

    const contentInput = page.getByPlaceholder(/Escribe la información fáctica y concisa/i)
    await contentInput.fill("Ofrecemos 30 días de garantía total en granos no abiertos y reembolso inmediato.")

    // Guardar
    const submitBtn = page.getByRole("button", { name: "Crear Bloque" })
    await submitBtn.click()

    // Verificar que el bloque aparece en el listado
    await expect(
      page.getByText("Políticas de Garantía y Reembolso").first()
    ).toBeVisible({ timeout: 5000 })
  })
})
