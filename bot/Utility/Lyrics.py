from selenium import webdriver
import time


def click_when_available(driver, xpath, max_time=None):
    start_time = time.time()
    i = 0
    while True:
        i += 1
        try:
            driver.find_element_by_xpath(xpath).click()
            return True
        except Exception:
            driver.execute_script(f"window.scrollTo(0, {500 * i});")
            pass
        if max_time and time.time() - start_time > max_time:
            return False


def click_until_text_changes(driver, click_xpath, text_xpath):
    """
    start_time = time.time()
    old_txt = driver.find_element_by_xpath(text_xpath).text
    while True:
        driver.find_element_by_xpath(click_xpath).click()
        new_txt = driver.find_element_by_xpath(text_xpath).text

        if new_txt != old_txt:
            return new_txt
        if max_time and time.time() - start_time > max_time:
            return new_txt
    """
    # Click Expand
    time.sleep(2)
    res = click_when_available(driver, click_xpath, max_time=3)
    if not res:
        print("Couldn't find")
        return ""
    # driver.find_element_by_xpath(click_xpath).click()

    # Get text
    time.sleep(2)
    element = driver.find_element_by_xpath(text_xpath)
    # elements = element.find_elements_by_tag_name("div")

    return element.text


def get_lyrics(search_string):
    op = webdriver.ChromeOptions()
    op.add_argument('--headless')
    driver = webdriver.Chrome(options=op)

    search_string = search_string.replace(" ", "+")
    url = f"https://www.google.com/search?q={search_string}+lyrics"
    print(url)
    driver.get(url)

    # click accept google's terms of service
    click_when_available(driver, "/html/body/div[3]/div[3]/span/div/div/div[3]/button[2]")

    text = click_until_text_changes(driver,
                                    "/html/body/div[8]/div/div[9]/div[1]/div/div[2]/div[2]/div/div/div[1]/div/div[1]/div[1]/g-more-link/div",
                                    "/html/body/div[8]/div/div[9]/div[1]/div/div[2]/div[2]/div/div/div[1]/div/div[1]/div[1]/span/div/div/div[2]/div/div/div/div/div/div[1]")
    driver.close()
    return text


if __name__ == "__main__":
    lyrics = get_lyrics("loud and clear")
    print(lyrics)
