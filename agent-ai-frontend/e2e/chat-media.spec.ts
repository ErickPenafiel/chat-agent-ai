import { test, expect } from "@playwright/test"

// PNG de 1 píxel: basta para comprobar el flujo de adjuntar, enviar y mostrar la imagen.
const PIXEL = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64"
)

test.describe("Adjuntos en el chat", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
    await page.getByRole("button", { name: "Simulador de Chat En vivo" }).click()
    await expect(page.getByRole("heading", { name: "Simulador de Chat en Vivo" })).toBeVisible()
  })

  test("adjuntar una imagen la muestra por enviar y en la burbuja del cliente", async ({ page }) => {
    await page.getByTestId("chat-image-input").setInputFiles({ name: "foto.png", mimeType: "image/png", buffer: PIXEL })
    await expect(page.getByAltText("Imagen por enviar")).toBeVisible()

    await page.getByPlaceholder("Escribe una pregunta para el agente...").fill("¿Qué café es este?")
    await page.keyboard.press("Enter")

    await expect(page.getByAltText("Imagen enviada")).toBeVisible()
    await expect(page.getByAltText("Imagen por enviar")).toBeHidden()
    await expect(page.locator(".rounded-tl-xs").nth(1)).toBeVisible({ timeout: 20000 })
  })

  test("se puede quitar la imagen antes de enviarla", async ({ page }) => {
    await page.getByTestId("chat-image-input").setInputFiles({ name: "foto.png", mimeType: "image/png", buffer: PIXEL })
    await page.getByRole("button", { name: "Quitar imagen" }).click()
    await expect(page.getByAltText("Imagen por enviar")).toBeHidden()
  })

  test("el botón de micrófono y el de imagen están disponibles", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Grabar nota de voz" })).toBeEnabled()
    await expect(page.getByRole("button", { name: "Adjuntar imagen" })).toBeEnabled()
  })
})
