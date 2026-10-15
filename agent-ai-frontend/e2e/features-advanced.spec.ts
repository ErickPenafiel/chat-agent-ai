import { test, expect } from "@playwright/test"

test.describe("Funcionalidades Avanzadas del Frontend", () => {
  test("debe permitir duplicar un bloque de conocimiento en la KB", async ({ page }) => {
    await page.goto("/")
    await page.getByRole("button", { name: /Base de Conocimiento/i }).click()
    await expect(page.getByRole("heading", { name: "Base de Conocimiento" })).toBeVisible()

    // Botón duplicar bloque
    const dupBtn = page.getByTitle("Duplicar bloque").first()
    await expect(dupBtn).toBeVisible()
    await dupBtn.click()

    // Debe mostrar la copia creada
    await expect(page.getByText(/\(Copia\)/i).first()).toBeVisible()
  })

  test("debe permitir crear y alternar entre múltiples sesiones de chat", async ({ page }) => {
    await page.goto("/")
    await page.getByRole("button", { name: "Simulador de Chat En vivo" }).click()
    await expect(page.getByRole("heading", { name: "Simulador de Chat en Vivo" })).toBeVisible()

    // Clic en Nueva Sesión
    const newSessionBtn = page.getByTitle("Crear nueva conversación independiente")
    await expect(newSessionBtn).toBeVisible()
    await newSessionBtn.click()

    // El selector debe reflejar la nueva conversación
    await expect(page.getByRole("combobox")).toBeVisible()
  })

  test("debe permitir avanzar paso a paso en el reproductor del grafo", async ({ page }) => {
    await page.goto("/")
    await page.getByRole("button", { name: /Flujo del Grafo/i }).click()
    await expect(page.getByRole("heading", { name: /Flujo del Grafo/i })).toBeVisible()

    // Botón Siguiente paso
    const stepBtn = page.getByRole("button", { name: "Siguiente" })
    await expect(stepBtn).toBeVisible()
    await stepBtn.click()

    // Badge del paso debe actualizarse
    await expect(page.getByText(/Paso:/i)).toBeVisible()
  })

  test("debe permitir ejecutar un ping de salud en los conectores", async ({ page }) => {
    await page.goto("/")
    await page.getByRole("button", { name: "Conectores" }).click()
    await expect(page.getByRole("heading", { name: "Conectores e Integraciones" })).toBeVisible()

    // Ping health en un conector
    const pingBtn = page.getByRole("button", { name: "Ping Health" }).first()
    await expect(pingBtn).toBeVisible()
    await pingBtn.click()

    // Debe mostrar ms de latencia
    await expect(page.getByText(/ms/i).first()).toBeVisible()
  })
})
