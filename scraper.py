#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located,
    element_to_be_clickable,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
import logging
import os
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
import ssl
import time


# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s (%(filename)s:%(lineno)d) %(levelname)s - %(message)s ",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log", mode="a", encoding="utf-8"),
    ],
)

logger = logging.getLogger("scraper")


def save_screenshot():
    if not save_screenshots:
        return
    timestamp = time.strftime("%Y%m%dT%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}"
    location = os.path.join("screenshots", f"{timestamp}.png")
    driver.save_screenshot(location)
    logger.info(f"Screenshot gespeichert unter {location}")


def open_website(url: str):
    logger.info(f"Öffnen der Webseite {url}")
    try:
        driver.get(url)
        save_screenshot()
    except Exception as e:
        logger.error(f"Fehler beim Öffnen: {e}")
        close_driver()
        raise


def close_driver():
    logger.info("Beenden des Browser-Treibers ...")
    driver.quit()


def accept_cookies():
    try:
        logger.info("Auf das Cookie-Banner warten ...")
        # Das Cookie-Banner ist ein Shadow-DOM-Element mit der ID "usercentrics-root"
        host = WebDriverWait(driver, 10).until(
            presence_of_element_located((By.ID, "usercentrics-cmp-ui"))
        )
        root = host.shadow_root

        save_screenshot()
        logger.info(
            "Prüfen, ob der Einwilligungsknopf vorhanden und anklickbar ist ..."
        )

        # `consent_button_clickable()` ist eine sogenannte "Erwartung" (Expectation) für Selenium.
        # Die Funktion prüft, ob der Akzeptieren-Knopf im Shadow DOM vorhanden und anklickbar ist.
        # WebDriverWait.until() verwendet sie, um sicherzustellen, dass der Button
        # vorhanden ist, bevor darauf geklickt wird.
        def consent_button_clickable(_driver) -> bool | WebElement:
            try:
                # Der Akzeptieren-Knopf hat die ID "accept"
                element = root.find_element(By.ID, "accept")
                return (
                    element
                    if element.is_displayed() and element.is_enabled()
                    else False
                )
            except NoSuchElementException:
                return False

        consent_button = WebDriverWait(driver, 10).until(consent_button_clickable)
        consent_button.click()
        save_screenshot()

    except Exception as e:
        logger.error(f"Fehler beim Annehmen der Cookies: {e}")


def select_product_size(size: str | int) -> bool:
    try:
        size_element = WebDriverWait(driver, 10).until(
            element_to_be_clickable(
                (By.XPATH, f"//div[@id='size-filters']//span[text()='{size}']")
            )
        )
        size_element.click()
        save_screenshot()
        logger.info(f"Produktgröße '{size}' erfolgreich ausgewählt.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Auswählen der Produktgröße: {e}")
    return False


def get_price() -> float | None:
    try:
        logger.info("Produktpreis ermitteln ...")
        price_element = driver.find_element(
            By.CSS_SELECTOR,
            "div#visualVariantFilter span.oopStage-variantThumbnailsFromPrice",
        )
        price = price_element.text
        # Euro-Zeichen entfernen und Komma in Punkt umwandeln,
        # anschließend den Preis in einen Float konvertieren.
        price = float(price.replace("€", "").replace(",", ".").strip())
        logger.info(f"Preis: {price} €")
        return price
    except Exception as e:
        logger.error(f"Fehler beim Ermitteln des Preises: {e}")
        return None


def send_email(subject: str, body: str) -> None:
    sender = os.getenv("sender")
    recipient = os.getenv("recipient")
    password = os.getenv("password")
    smtp_server = os.getenv("smtp_server")
    smtp_port = os.getenv("smtp_port")
    if not all([sender, recipient, password, smtp_server, smtp_port]):
        logger.error("E-Mail-Konfiguration nicht vollständig.")
        return
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender, password)
            msg = EmailMessage()
            msg.set_content(body)
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = recipient
            server.send_message(msg)
            logger.info(f"E-Mail erfolgreich an {recipient} gesendet.")
    except Exception as e:
        logger.error(f"Fehler beim Senden der E-Mail: {e}")


driver = None
save_screenshots = False


def job():
    global driver, save_screenshots
    # Eigenschaften des heißbegehrten Produkts festlegen
    product = "Skechers Elite Flex Corriedale 78803 CCL Grey"
    size = "44"
    my_limit = 70.00
    url = "https://www.idealo.de/preisvergleich/OffersOfProduct/200671888_-elite-flex-corriedale-78803-ccl-grey-skechers.html"

    firefox_options = webdriver.FirefoxOptions()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(options=firefox_options)

    open_website(url)
    accept_cookies()
    available = select_product_size(size)
    if not available:
        logger.warning(f"Produktgröße '{size}' ist nicht verfügbar.")
    else:
        price = get_price()
        if price is not None:
            price_formatted = f"{price:.2f}".replace(".", ",")
            my_limit_formatted = f"{my_limit:.2f}".replace(".", ",")
            if price < my_limit:
                logger.info(
                    f"Preis {price} liegt unter dem Limit {my_limit_formatted} €. E-Mail wird gesendet ..."
                )
                send_email(
                    f"Preisalarm für {product}",
                    f"Der Preise für {product} in Größe {size} liegt aktuell bei {price_formatted} € "
                    f"und damit unter deinem Limit von {my_limit_formatted} €.\n\n"
                    f"Hier klicken, um zu shoppen: {driver.current_url}",
                )
            else:
                logger.info(
                    f"{price_formatted} € liegt über dem Limit {my_limit_formatted} €. Keine Mail verschickt."
                )
        else:
            logger.error("Produktpreis konnte nicht ermittelt werden.")
    close_driver()


def main():
    load_dotenv()
    global save_screenshots
    save_screenshots = os.getenv("save_screenshots", "False").lower() == "true"
    interval = float(os.getenv("interval", 300))
    logger.info(f"Job wird alle {interval:.1f} Sekunden ausgeführt.")
    while True:
        job()
        logger.info(f"{interval:.1f} Sekunden bis zum nächsten Job warten ...")
        time.sleep(interval)


if __name__ == "__main__":
    main()
