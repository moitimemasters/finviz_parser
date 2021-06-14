from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from PIL import Image, ImageDraw, ImageFont


import io
import time
import os
import argparse

os.environ['WDM_LOG_LEVEL'] = '0'


def set_driver():
    print("started new instance of driver...")
    # setting up driver
    options = Options()
    options.add_argument("--headless")
    windows_useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
    options.add_argument("window-size=1920x1080")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-web-security")
    options.add_argument('--log-level=3')
    options.add_argument(f"user-agent={windows_useragent}")
    options.add_argument("--disable-xss-auditor")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    executable = ChromeDriverManager().install()
    driver = webdriver.Chrome(executable_path=executable, options=options, service_log_path="NUL")
    driver.set_window_position(0, 0)
    driver.set_window_size(3840, 2160)
    return driver


def scroll_down(driver):
    total_width = driver.execute_script("return document.body.offsetWidth")
    total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
    viewport_width = driver.execute_script("return document.body.clientWidth")
    viewport_height = driver.execute_script("return window.innerHeight")

    rectangles = []

    i = 0
    while i < total_height:
        ii = 0
        top_height = i + viewport_height
        if top_height > total_height:
            top_height = total_height
        while ii < total_width:
            top_width = ii + viewport_width
            if top_width > total_width:
                top_width = total_width
            rectangles.append((ii, i, top_width, top_height))
            ii = ii + viewport_width
        i = i + viewport_height
    previous = None
    part = 0

    for rectangle in rectangles:
        if not previous is None:
            driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
            time.sleep(0.5)
        # time.sleep(0.2)

        if rectangle[1] + viewport_height > total_height:
            offset = (rectangle[0], total_height - viewport_height)
        else:
            offset = (rectangle[0], rectangle[1])

        previous = rectangle

    return (total_height, total_width)


def hide_info(driver):
    js_script = '''
        element = document.getElementsByClassName('info');
        element[0].style.display = 'none';
        '''
    driver.execute_script(js_script)


def create_caption(caption, W, H, color):
    msg = caption
    img = Image.new("RGBA", (W, H), "#262931")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 36, encoding="utf-8")
    w, h = draw.textsize(msg, font=font)
    draw.text(((W - w) / 2, (H - h) / 2), msg, fill=color, font=font, encoding="utf-8")
    return img


def concat_images(img1, img2):
    width = 1920
    height = 1080
    total_height = img1.size[1] + img2.size[1]
    total_width = img1.size[0]
    offset_y = (height - total_height) // 2
    offset_x = (width - total_width) // 2
    new_img = Image.new("RGBA", (width, height), "#262931")
    new_img.paste(img1, (offset_x, offset_y))
    new_img.paste(img2, (offset_x, offset_y + img1.size[1]))
    return new_img


def process_image(img, caption):
    # cropping
    w, h = img.size
    img = img.crop((19, 0, w, 830))
    caption_img = create_caption(caption, w - 19, 200, "white")
    return concat_images(caption_img, img)
    # img.save("test2.png")


def test_image(image_fn, output_fn):
    img = Image.open(image_fn)
    img1 = process_image(img, "тестовое описание")
    img1.save(output_fn)


def fix_padding(driver):
    driver.execute_script('''
        let map_element = document.getElementById("map");
        map_element.style.padding = "10px";
    ''')


def remove_ads(driver):
    print("removing ads...")
    all_iframes = driver.find_elements_by_tag_name("iframe")
    if len(all_iframes) > 0:
        print("Ad Found\n")
        driver.execute_script("""
            var elems = document.getElementsByTagName("iframe");
            if (elems.length >= 1) {
                for(el of elems) {
                    console.log(el);
                    el.remove();
                }
            }
                              """)
        print('Total Ads: ' + str(len(all_iframes)))
    else:
        print('No frames found')


def get_map(driver, link, img_path, caption):
    map_xpath = '//*[@id="map"]'
    wait = WebDriverWait(driver, 10)
    print("loading page...")
    driver.get(link))
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, map_xpath)))
        print("loaded...")
    except Exception:
        print("something went wrong on loading the map.")
    print("waiting for ads...")
    time.sleep(3)
    print("hiding info...")
    hide_info(driver)
    # fix_padding(driver)
    map_element = driver.find_element_by_xpath(map_xpath)
    remove_ads(driver)
    print("downloading image...")
    imageStream = io.BytesIO(map_element.screenshot_as_png)
    img = Image.open(imageStream)
    img.save(img_path)
    print("downloaded.")
    print("processing image...")
    img = Image.open(img_path)
    img = process_image(img, caption)
    img.save(img_path)
    print("image %s has been saved." % img_path)


def main(link, image_path, caption):
    driver = set_driver()
    get_map(driver, link, image_path, caption)
    driver.quit()
    print("closed driver instance.")


if __name__ == '__main__':
    # main("https://finviz.com/map.ashx?t=sec", "image-1.png", "первая карта")
    parser = argparse.ArgumentParser(description="Procecss link to finviz, output path, caption on image")
    parser.add_argument("link", metavar="L", type=str, help="a link to finviz map")
    parser.add_argument("output_path", metavar="O", type=str, help="output path of map (.../some/thing/name.png)")
    parser.add_argument("caption", metavar="C", type=str, help="caption that will be written on top of the image", default="", nargs="?")
    args = parser.parse_args()
    main(args.link, args.output_path, args.caption)
