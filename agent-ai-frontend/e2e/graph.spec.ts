import { test, expect } from "@playwright/test"

test.describe("Flujo del Grafo con React Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
    await page.getByRole("button", { name: /Flujo del Grafo/i }).click()
    await expect(
      page.getByRole("heading", { name: /Flujo del Grafo/i })
    ).toBeVisible()
  })

  test("debe renderizar el lienzo de React Flow con los nodos de LangGraph", async ({
    page,
  }) => {
    // Verificar nodos clave en el canvas
    await expect(page.getByText("START (Webhook)")).toBeVisible()
    await expect(page.getByTestId("rf__node-intent").first()).toBeVisible()
    await expect(page.getByText("retrieval (KB Search)")).toBeVisible()
    await expect(page.getByTestId("rf__node-handoff").first()).toBeVisible()
    await expect(page.getByText("END (Respuesta Enviada)")).toBeVisible()
  })

  test("debe permitir simular la ruta de escalado a humano", async ({ page }) => {
    const simBtn = page.getByRole("button", { name: "Escalado" })
    await expect(simBtn).toBeVisible()
    await simBtn.click()

    // El botón de Restablecer debe aparecer
    await expect(page.getByTitle("Restablecer simulación")).toBeVisible()
  })

  test("debe mostrar el panel de detalle al hacer clic en un nodo", async ({
    page,
  }) => {
    const intentNode = page.getByTestId("rf__node-intent").first()
    await intentNode.click()

    await expect(page.getByText("src/nodes/intent.py")).toBeVisible()
    await expect(
      page.getByText(/Clasifica la consulta entre/i).first()
    ).toBeVisible()
  })
})
