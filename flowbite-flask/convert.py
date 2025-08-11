import asyncio
from playwright.async_api import async_playwright

async def convert_html_to_pdf(input_html, output_pdf):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Load local HTML file content
        with open(input_html, 'r', encoding='utf-8') as f:
            content = f.read()

        # Set HTML content
        await page.set_content(content, wait_until="networkidle")
        
        # Wait to ensure proper rendering
        await page.wait_for_timeout(1000)

        # Set viewport to mimic A4 width in pixels (~794px)
        await page.set_viewport_size({"width": 1123, "height": 1587})  # A4 portrait

        # Export to PDF
        await page.pdf(
            path=output_pdf,
            format="A4",
            landscape=False,
            print_background=True,
            margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"}
        )

        await browser.close()

if __name__ == "__main__":
    asyncio.run(convert_html_to_pdf("core_functionality/resume10.html", "generated_resume.pdf"))
