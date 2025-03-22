from ifood_scraper import configurar_driver

if __name__ == "__main__":
    driver = configurar_driver(headless=False)
    driver.get("https://www.google.com")
    print("Página carregada com sucesso!")
    driver.quit()