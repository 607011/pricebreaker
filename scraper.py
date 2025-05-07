#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located,
    element_to_be_clickable,
)
from selenium.webdriver.support.ui import WebDriverWait
import logging
import os
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
import ssl
import sys
import time
import yaml

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
    timestamp = (
        time.strftime("%Y%m%dT%H%M%S") + f".{int(time.time() * 1000) % 1000:03d}"
    )
    location = os.path.join("screenshots", f"{timestamp}.png")
    driver.save_screenshot(location)
    logger.info(f"Screenshot saved under {location}")


def open_website(url: str):
    logger.info(f"Opening the web page {url} ...")
    try:
        driver.get(url)
        save_screenshot()
    except Exception as e:
        logger.error(f"Error opening the web page: {e}")
        shutdown()
        raise


def shutdown():
    try:
        if driver.service.process and driver.service.process.poll() is None:
            logger.info("Closing browser driver ...")
            driver.quit()
    except Exception as e:
        logger.warning(f"Error while closing the browser driver: {e}")


def accept_cookies():
    try:
        logger.info("Waiting for the cookie consent banner ...")
        # The cookie consent banner lives in a shadow DOM and has the ID "usercentrics-cmp-ui"
        host = WebDriverWait(driver, 10).until(
            presence_of_element_located((By.ID, "usercentrics-cmp-ui"))
        )
        root = host.shadow_root

        save_screenshot()
        logger.info("Checking if the 'accept' button is present ...")

        # `consent_button_clickable()` is a so-called expected condition in Selenium.
        # The function checks, if the 'accept' button is present.
        # WebDriverWait.until() uses the function to make sure it's clickable
        # before clicking it.
        def consent_button_clickable(_driver: WebDriver) -> WebElement | None:
            element = root.find_element(By.ID, "accept")
            return element if element.is_displayed() and element.is_enabled() else None

        consent_button = WebDriverWait(driver, 10).until(consent_button_clickable)
        consent_button.click()
        save_screenshot()

    except Exception as e:
        logger.error(f"Error accepting cookies: {e}")


def select_product_size(size: str | int) -> bool:
    try:
        size_element = WebDriverWait(driver, 10).until(
            element_to_be_clickable(
                (By.XPATH, f"//div[@id='size-filters']//span[text()='{size}']")
            )
        )
        size_element.click()
        save_screenshot()
        logger.info(f"Product size '{size}' successfully selected.")
        return True
    except Exception as e:
        logger.error(f"Error selecting product size: {e}")
    return False


def get_price() -> float | None:
    try:
        logger.info("Fetching prize ...")
        price_element = driver.find_element(
            By.CSS_SELECTOR,
            "div#visualVariantFilter span.oopStage-variantThumbnailsFromPrice",
        )
        price = price_element.text
        price = float(price.replace("€", "").replace(",", ".").strip())
        logger.info(f"Prize: {price} €")
        return price
    except Exception as e:
        logger.error(f"Error fetching prize: {e}")
        return None


def send_email(subject: str, body: str) -> None:
    sender = os.getenv("sender")
    recipient = os.getenv("recipient")
    password = os.getenv("password")
    smtp_server = os.getenv("smtp_server")
    smtp_port = os.getenv("smtp_port")
    if not all([sender, recipient, password, smtp_server, smtp_port]):
        logger.error("Email configuration is incomplete.")
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
            logger.info(f"Email successfully sent to {recipient}.")
    except Exception as e:
        logger.error(f"Error sending mail: {e}")


driver = None
save_screenshots = False


def job(config_file: str = "config.yaml"):
    global driver, save_screenshots
    with open(config_file, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    product = config.get("product", "Skechers Elite Flex Corriedale 78803 CCL Grey")
    size = config.get("size", "44")
    my_limit = float(config.get("limit", 100))
    url = config.get(
        "url",
        "https://www.idealo.de/preisvergleich/OffersOfProduct/200671888_-elite-flex-corriedale-78803-ccl-grey-skechers.html",
    )

    firefox_options = webdriver.FirefoxOptions()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(options=firefox_options)

    open_website(url)
    accept_cookies()
    available = select_product_size(size)
    if not available:
        logger.warning(f"Size '{size}' is not available.")
    else:
        price = get_price()
        if price is not None:
            price_formatted = f"{price:.2f}".replace(".", ",")
            my_limit_formatted = f"{my_limit:.2f}".replace(".", ",")
            if price < my_limit:
                logger.info(
                    f"Prize {price} is below limit of {my_limit_formatted} €. Sending email ..."
                )
                send_email(
                    f"Prize alert for {product}",
                    f"The prize for {product} in size {size} currently is {price_formatted} € "
                    f"which is below your limit of {my_limit_formatted} €.\n\n"
                    f"Click to buy: {driver.current_url}",
                )
            else:
                logger.info(
                    f"{price_formatted} € is above the limit of {my_limit_formatted} €. No email sent."
                )
        else:
            logger.error("Could not fetch prize of product.")
    shutdown()


def main() -> int:
    load_dotenv()
    global save_screenshots
    save_screenshots = os.getenv("save_screenshots", "False").lower() == "true"
    interval = float(os.getenv("interval", 300))
    logger.info(f"Job will be executed every {interval:.1f} seconds.")
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    if not os.path.exists(config_file):
        logger.error(f"Config file '{config_file}' does not exist.")
        return 1
    if not os.path.isfile(config_file):
        logger.error(f"Config file '{config_file}' is not a file.")
        return 2
    if not os.access(config_file, os.R_OK):
        logger.error(f"Config file '{config_file}' is not readable.")
        return 3
    try:
        while True:
            job()
            logger.info(
                f"Waiting {interval:.1f} seconds until next execution of job ..."
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Execution interrupted by user. Exiting gracefully ...")
        if driver:
            shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
