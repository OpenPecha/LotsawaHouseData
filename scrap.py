"""
Lotsawa House EPUB Scraper (Selenium + Logging)
From the Aspiration Prayers page, expand all sections, visit each text page, and download EPUB.
"""

import os
import sys
import time
import shutil
import logging
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException


class LotsawaEPUBScraper:
    def __init__(self, base_url, output_dir="lotsawa_epubs", delay=1, headless=False):
        self.base_url = base_url
        self.output_dir = Path(output_dir).absolute()
        self.delay = delay
        self.headless = headless # to give condition whether to run without opening chrome browser, send false to see chrome browser opened and runnning the process

        self.driver = None #The Selenium Chrome WebDriver used to load pages and interact with the DOM (navigate, find elements, run JS).
        self.wait = None #The WebDriverWait object used to wait for specific conditions to be met before proceeding.
        self.logger = self._configure_logging()

        self._ensure_directories()
        self._init_browser()

    def _configure_logging(self):
        logger = logging.getLogger("lotsawa.scraper")
        logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

            # Console handler (INFO)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(fmt)
            logger.addHandler(ch)

            # File handler (DEBUG)
            logs_dir = Path("logs")
            logs_dir.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(logs_dir / "scrape.log")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(fmt)
            logger.addHandler(fh)

        return logger

    def _ensure_directories(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directory: {self.output_dir}")

    def _init_browser(self):
        """
        chrome_options = Options()
        What: Creates a Chrome configuration object you can attach flags and preferences to.
        Use case: You need to set download folder, headless mode, stability flags before launching Chrome.
        """
        chrome_options = Options()
        """
        
        if self.headless: chrome_options.add_argument("--headless=new")
        What: If headless is True, tells Chrome to run without a visible window.
        Use case: Run on CI/servers or when you don't want a UI to pop up.
        Example: Construct the scraper with headless=True to scrape in the background.
        """
        if self.headless:
            chrome_options.add_argument("--headless=new")

        prefs = {
            "download.default_directory": str(self.output_dir), #sets download path form the self.output-dir
            "download.prompt_for_download": False, # prevents the browser from asking for confirmation to download the file which helps in automatically downloading the file
            "download.directory_upgrade": True, # allows the browser to upgrade the download directory if it is not present
            "safebrowsing.enabled": True, # enables safe browsing features to prevent malicious downloads
        }
        chrome_options.add_experimental_option("prefs", prefs) #adds the preferences to the chrome options
        chrome_options.add_argument("--no-sandbox") #adds the no sandbox argument to the chrome options
        """
        Why we disable it (--no-sandbox) sometimes:

        When running Chrome in Docker or headless environments, Chrome’s sandbox can’t always create those isolated processes (because Docker already does isolation).
        If both Docker and Chrome try to sandbox at the same t ime → crash.

        So, --no-sandbox says:

        “It’s okay Chrome, I trust this environment. Don’t create your own sandbox.”
        """
        chrome_options.add_argument("--disable-dev-shm-usage") #adds the disable dev shm usage argument to the chrome options, Prevents random Chrome crashes due to low shared memory. Sometimes /dev/shm is too small in Docker or server environments, causing Chrome to crash or freeze.

        self.driver = webdriver.Chrome(options=chrome_options) #Launches a new Chrome instance with those options.
        """
        self.wait = WebDriverWait(self.driver, 20)
        What: A helper that waits up to 20 seconds for conditions (elements present/clickable).
        Use case: Pages need time to load; you can do:
        Example: self.wait.until(EC.presence_of_element_located((By.ID, "downloads")))
        """
        self.wait = WebDriverWait(self.driver, 20) 
        self.logger.info("Initialized Chrome WebDriver")

    def _expand_all_sections(self):
        self.logger.info(f"Opening topic page: {self.base_url}")
        self.driver.get(self.base_url) #
        # Dismiss cookie banner if present on first load
        self._dismiss_cookie_banner()

        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.subheadings")))
        except Exception as e:
            self.logger.error(f"Subheadings container not found: {e}")
            return

        details = self.driver.find_elements(By.CSS_SELECTOR, "div.subheadings details.accordion[name='accordion']")
        self.logger.info(f"Found {len(details)} sections (details.accordion)")

        for d in details:
            try:
                self.driver.execute_script("arguments[0].setAttribute('open','')", d)
            except Exception:
                pass
        self.logger.info("Expanded all sections")
        time.sleep(self.delay)

    def _collect_text_links(self):
        url_to_subs = {}
        order = []
        details = self.driver.find_elements(By.CSS_SELECTOR, "div.subheadings details.accordion[name='accordion']")

        for d in details:
            # Subheading title from the accordion's summary
            subheading = d.find_element(By.TAG_NAME, "summary").text.strip()
            anchors = d.find_elements(By.CSS_SELECTOR, "div.text-card a.title")
            for a in anchors:
                href = a.get_attribute("href")
                if not href:
                    continue
                full_url = urljoin(self.base_url, href)
                if full_url not in url_to_subs:
                    url_to_subs[full_url] = []
                    order.append(full_url)
                if subheading not in url_to_subs[full_url]:
                    url_to_subs[full_url].append(subheading)

        grouped = [(u, url_to_subs[u]) for u in order]

        self.logger.info(f"Collected {len(grouped)} text links")
        if grouped:
            self.logger.debug(f"First few links: {[u for u, _ in grouped[:5]]}")
        return grouped

    def _dismiss_cookie_banner(self):
        """Attempt to accept or hide the cookie banner if it is displayed."""
        try:
            banner = self.driver.find_element(By.ID, "tasty-cookies")
        except Exception:
            return

        try:
            if banner.is_displayed():
                # Try click Accept button/link inside banner
                try:
                    accept = banner.find_element(
                        By.XPATH,
                        ".//button[contains(., 'Accept')] | .//a[contains(., 'Accept')]"
                    )
                    self.logger.info("Accepting cookie banner")
                    try:
                        accept.click()
                    except Exception:
                        # Fallback to JS click
                        self.driver.execute_script("arguments[0].click();", accept)
                    time.sleep(0.5)
                except Exception:
                    # Fallback: hide banner via JS
                    self.logger.info("Hiding cookie banner via JavaScript")
                    self.driver.execute_script("arguments[0].style.display='none';", banner)
                    time.sleep(0.2)
        except Exception:
            pass

    def _wait_for_download(self, before_set, timeout=120):
        start = time.time()
        while time.time() - start < timeout:
            current = set(self.output_dir.glob("*"))
            new = list(current - before_set)
            temp_present = any(p.suffix.lower() == ".crdownload" for p in current)
            epubs = [p for p in new if p.suffix.lower() == ".epub"]
            if epubs and not temp_present:
                # pick the most recent epub and confirm size has stabilized
                target = max(epubs, key=lambda p: p.stat().st_mtime)
                try:
                    size1 = target.stat().st_size
                except FileNotFoundError:
                    time.sleep(0.5)
                    continue
                time.sleep(0.5)
                try:
                    if target.exists() and target.stat().st_size == size1:
                        return target
                except FileNotFoundError:
                    pass
            time.sleep(0.5)
        return None

    def _unique_path(self, path: Path) -> Path:
        """Return a non-conflicting path by appending ' (n)' if needed."""
        if not path.exists():
            return path
        stem, ext = path.stem, path.suffix
        n = 1
        while True:
            candidate = path.with_name(f"{stem} ({n}){ext}")
            if not candidate.exists():
                return candidate
            n += 1

    def _download_epub_from_text_page(self, url, subfolder=None):
        self.logger.info(f"Visiting: {url}")
        self.driver.get(url)
        time.sleep(self.delay)

        # Attempt to switch to English if available before proceeding
        self._dismiss_cookie_banner()
        try:
            # Ensure the page-level language list is present before searching for the link
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "lang-list")))
            except Exception:
                pass
            english_links = self.driver.find_elements(By.XPATH, "//*[@id='lang-list']//a[normalize-space()='English']")
            if english_links:
                self.logger.info("Switching to English")
                link = english_links[0]
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.2)
                except Exception:
                    pass
                old_url = self.driver.current_url
                try:
                    link.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", link)
                # Wait for navigation or English content to appear
                try:
                    self.wait.until(lambda d: ("/bo/" not in d.current_url) or bool(d.find_elements(By.CSS_SELECTOR, "#maintext p.en")))
                except Exception:
                    pass
                time.sleep(self.delay)
        except Exception as e:
            self.logger.info(f"English link not found or click failed; proceeding: {e}")

        # Detect verse content on the page to decide if we should create an extra language copy
        extra_language_dir = None
        try:
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "maintext")))
            except Exception:
                pass
            current_url = self.driver.current_url
            is_tibetan_page = "/bo/" in current_url
            # Class-based hints (present on many pages)
            has_bo_class = bool(self.driver.find_elements(By.CSS_SELECTOR, "#maintext p.bo"))
            has_en_class = bool(self.driver.find_elements(By.CSS_SELECTOR, "#maintext p.en"))
            has_en_trans_class = bool(self.driver.find_elements(By.CSS_SELECTOR, "#maintext p.en-trans"))
            # Script-based Tibetan detection to handle pages without classes
            maintext_elms = self.driver.find_elements(By.ID, "maintext")
            maintext_text = maintext_elms[0].text if maintext_elms else ""
            tibetan_script_present = any('\u0f00' <= ch <= '\u0fff' for ch in maintext_text)
            self.logger.debug(
                f"Page url='{current_url}', tib_page={is_tibetan_page} | "
                f"classes -> bo={has_bo_class}, en={has_en_class}, en-trans={has_en_trans_class} | "
                f"tibetan_script_present={tibetan_script_present}"
            )
            # English page: only copy when there is no Tibetan content (neither class nor script)
            if not is_tibetan_page:
                has_tibetan_content = has_bo_class or tibetan_script_present
                if not has_tibetan_content:
                    extra_language_dir = "English"
            else:
                # Tibetan page: only copy when there is clearly no English content
                if not has_en_class and not has_en_trans_class:
                    extra_language_dir = "Tibetan"
            if extra_language_dir:
                self.logger.info(f"Detected single-language page: {extra_language_dir}")
        except Exception as e:
            self.logger.debug(f"Verse tag detection failed; proceeding without extra language copy: {e}")

        # Wait for downloads block
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "downloads")))
        except Exception as e:
            self.logger.warning(f"No downloads block on page: {e}")
            return False

        # Ensure cookie banner is not covering controls
        self._dismiss_cookie_banner()

        # Find and click EPUB
        try:
            epub_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//div[@id='downloads']//a[contains(., 'EPUB')]"))
            )
            # Scroll into view for safety
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", epub_btn)
                time.sleep(0.2)
            except Exception:
                pass
        except Exception as e:
            self.logger.warning(f"EPUB button not found: {e}")
            return False

        before = set(self.output_dir.glob("*"))
        self.logger.debug("Clicking EPUB button...")
        try:
            epub_btn.click()
        except ElementClickInterceptedException as e:
            self.logger.error(f"Failed to click EPUB (intercepted): {e}")
            # Try dismissing cookie again then JS click fallback
            self._dismiss_cookie_banner()
            try:
                self.driver.execute_script("arguments[0].click();", epub_btn)
            except Exception as e2:
                self.logger.error(f"JS click fallback also failed: {e2}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to click EPUB: {e}")
            # JS click fallback
            try:
                self.driver.execute_script("arguments[0].click();", epub_btn)
            except Exception as e2:
                self.logger.error(f"JS click fallback also failed: {e2}")
                return False

        downloaded = self._wait_for_download(before)
        if downloaded:
            self.logger.info(f"Downloaded: {downloaded.name}")
            final_path = downloaded
            # If a subfolder is specified, move the downloaded file into that subfolder
            if subfolder:
                safe_subfolder = "".join(
                    c for c in subfolder
                    if c.isalnum() or c in (" ", "-", "_") or ('\u0f00' <= c <= '\u0fff')
                ).strip()
                safe_subfolder = unicodedata.normalize("NFC", safe_subfolder)
                if not safe_subfolder:
                    safe_subfolder = "Misc"
                target_dir = self.output_dir / safe_subfolder
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = self._unique_path(target_dir / downloaded.name)
                try:
                    downloaded.replace(target_path)
                    final_path = target_path
                    self.logger.info(f"Moved to subfolder: {safe_subfolder}")
                except Exception as e:
                    self.logger.warning(f"Failed to move file into subfolder '{safe_subfolder}': {e}")
            # After moving to primary subfolder, optionally copy to top-level language directory
            if extra_language_dir:
                try:
                    lang_dir = self.output_dir / extra_language_dir
                    lang_dir.mkdir(parents=True, exist_ok=True)
                    lang_target = self._unique_path(lang_dir / final_path.name)
                    shutil.copy2(final_path, lang_target)
                    self.logger.info(f"Copied to language folder: {extra_language_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to copy into language folder '{extra_language_dir}': {e}")

            # If page appears English-only, also fetch the Tibetan EPUB by clicking the Tibetan link
            # and move that EPUB into the /Tibetan directory.
            if extra_language_dir == "English":
                try:
                    # Find the Tibetan link under the page-level language list
                    tib_link_candidates = self.driver.find_elements(
                        By.XPATH,
                        "//*[@id='lang-list']//span[contains(@class,'TibetanInlineEnglish')]/ancestor::a[1]"
                    )
                    if tib_link_candidates:
                        tib_link = tib_link_candidates[0]
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tib_link)
                            time.sleep(0.2)
                        except Exception:
                            pass
                        try:
                            tib_link.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", tib_link)
                        # Wait for Tibetan page download block
                        try:
                            self.wait.until(EC.presence_of_element_located((By.ID, "downloads")))
                        except Exception:
                            pass
                        self._dismiss_cookie_banner()
                        try:
                            tib_epub_btn = self.wait.until(
                                EC.element_to_be_clickable((By.XPATH, "//div[@id='downloads']//a[contains(., 'EPUB')]"))
                            )
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tib_epub_btn)
                                time.sleep(0.2)
                            except Exception:
                                pass
                        except Exception as e:
                            self.logger.warning(f"Tibetan EPUB button not found: {e}")
                            tib_epub_btn = None
                        if tib_epub_btn:
                            tib_before = set(self.output_dir.glob("*"))
                            try:
                                tib_epub_btn.click()
                            except ElementClickInterceptedException:
                                self._dismiss_cookie_banner()
                                try:
                                    self.driver.execute_script("arguments[0].click();", tib_epub_btn)
                                except Exception:
                                    tib_epub_btn = None
                            except Exception:
                                try:
                                    self.driver.execute_script("arguments[0].click();", tib_epub_btn)
                                except Exception:
                                    tib_epub_btn = None
                            if tib_epub_btn:
                                tib_downloaded = self._wait_for_download(tib_before)
                                if tib_downloaded:
                                    try:
                                        tib_dir = self.output_dir / "Tibetan"
                                        tib_dir.mkdir(parents=True, exist_ok=True)
                                        tib_target = self._unique_path(tib_dir / tib_downloaded.name)
                                        tib_downloaded.replace(tib_target)
                                        self.logger.info("Moved Tibetan EPUB to language folder: Tibetan")
                                    except Exception as e:
                                        self.logger.warning(f"Failed to move Tibetan EPUB into language folder: {e}")
                except Exception as e:
                    self.logger.warning(f"Failed to fetch Tibetan EPUB via language switch: {e}")
            return final_path
        else:
            self.logger.warning("Timed out waiting for download to complete")
            return None

    def scrape_all(self):
        self.logger.info("=" * 60)
        self.logger.info("Lotsawa House EPUB Scraper (Selenium)")
        self.logger.info("=" * 60)
        self.logger.info(f"Base URL: {self.base_url}")

        self._expand_all_sections()
        items = self._collect_text_links()

        # Process all collected items without test filtering

        total = len(items)
        success = 0
        failed = 0

        for idx, (url, subfolders) in enumerate(items, 1):
            self.logger.info(f"[{idx}/{total}]")
            if not subfolders:
                self.logger.warning("No subheading found; skipping")
                failed += 1
                time.sleep(self.delay)
                continue
            primary = subfolders[0]
            final_path = self._download_epub_from_text_page(url, subfolder=primary)
            if not final_path:
                failed += 1
                time.sleep(self.delay)
                continue
            # Copy into additional subheading folders
            for extra in subfolders[1:]:
                safe_extra = "".join(
                    c for c in extra
                    if c.isalnum() or c in (" ", "-", "_") or ('\u0f00' <= c <= '\u0fff')
                ).strip()
                safe_extra = unicodedata.normalize("NFC", safe_extra)
                if not safe_extra:
                    safe_extra = "Misc"
                target_dir = self.output_dir / safe_extra
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = self._unique_path(target_dir / final_path.name)
                try:
                    shutil.copy2(final_path, target_path)
                    self.logger.info(f"Copied to subfolder: {safe_extra}")
                except Exception as e:
                    self.logger.warning(f"Failed to copy into subfolder '{safe_extra}': {e}")
            success += 1
            time.sleep(self.delay)

        self.logger.info("=" * 60)
        self.logger.info("SCRAPING COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Total texts processed: {total}")
        self.logger.info(f"Successfully downloaded: {success}")
        self.logger.info(f"Failed: {failed}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info("=" * 60)

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        finally:
            self.driver = None


def main():
    BASE_URL = "https://www.lotsawahouse.org/bo/topics/prayers/"
    OUTPUT_DIR = "lotsawahouse_prayers"  # this is the directory where the epub files will be downloaded
    DELAY = 1  # seconds between actions
    HEADLESS = False  # set True to run headless, False to see chrome browser opened and runnning the process

    scraper = LotsawaEPUBScraper(
        base_url=BASE_URL,
        output_dir=OUTPUT_DIR,
        delay=DELAY,
        headless=HEADLESS,
    )

    try:
        scraper.scrape_all()
    except KeyboardInterrupt:
        logging.getLogger("lotsawa.scraper").warning("Scraping interrupted by user")
        sys.exit(1)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()


