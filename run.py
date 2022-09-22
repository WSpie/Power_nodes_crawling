import time
import os, sys
from PIL import Image
import re
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from logger import IterLog
import numpy as np
import pandas as pd

dir_path = 'captures'

logger = IterLog()

key_dict = {'up': Keys.PAGE_UP, 'down': Keys.PAGE_DOWN, 'left': Keys.HOME, 'right': Keys.END, '-': Keys.SUBTRACT}

class HumanOps(unittest.TestCase):
    def __init__(self, driver):
        self.driver = driver
        self.action = ActionChains(self.driver)
        self.ops = ''
    
    def reset_mouse_pos(self):
        self.ops = 'Reset mouse position and clicked'
        self.action.move_to_element_with_offset(self.driver.find_element(By.TAG_NAME, 'body'), 0, 0).click()
    
    def click_coord_mouse(self, x_coord, y_coord):
        self.ops = f'Moved to ({x_coord}, {y_coord}) and clicked'
        self.action.move_by_offset(x_coord, y_coord).click().perform()

    def drag_drop_mouse(self, source, xoffset, yoffset):
        self.ops = f'Dragged and dropped to ({xoffset}, {yoffset})'
        self.action.drag_and_drop_by_offset(source, xoffset, yoffset).perform()
    
    def press_key(self, key):
        inv_key_dict = {v: k for k, v in key_dict.items()}
        self.ops = f'Pressed key "{inv_key_dict[key]}"'
        self.action.send_keys(key).perform()

    def hold_key(self, key, time_continue=None):
        self.ops = f'Pressed key "{key}" for {time_continue} seconds'
        self.action.key_down(Keys.CONTROL).send_keys(key).perform()
        if time_continue:
            time.sleep(time_continue)
        self.action.key_up(Keys.CONTROL).perform()

    def update(self, driver):
        self.driver = driver
        self.action = ActionChains(self.driver)

    def report(self, logger):
        logger.info(self.ops)
 
def config():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--incognito')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def load_and_relocate(driver):
    # load url
    url = 'https://miluma.lumapr.com/outages/outageMap'
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'jss56')))
    # manual operations
    ops = HumanOps(driver)
    # left click for entering keys
    ops.reset_mouse_pos()
    ops.click_coord_mouse(0, 100)
    WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'jss56')))
    ops.report(logger)
    # zoom out
    ops.press_key(Keys.SUBTRACT)
    WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'jss56')))
    ops.report(logger)
    # relocate to top left
    search_cnt = 0
    while True:
        try:
            time.sleep(1)
            WebDriverWait(driver, 10).until(EC.visibility_of_any_elements_located((By.CLASS_NAME, 'jss56')))
            ops.press_key(key_dict['left'])
            ops.report(logger)
            driver.save_screenshot('capture_start.png')
            search_cnt += 1
            if search_cnt > 10:
                print('Error relocated, end driver')
                driver.close()
                sys.exit(0)
        except:
            print('Relocated')
            break
    return driver

def contour_map(driver):
    df_path = 'power.csv'
    infos = np.array([])
    # decide the route
    routes = ['left', 'down', 'right']
    dir_ops = [1]*6+[0]+[-1]*5+[0]+[1]*5+[0]+[-1]*5
    dir_ops_unique = list(set(dir_ops))
    dir_ops_unique.sort()
    dir_dict = dict(zip(dir_ops_unique, routes))
    # start contouring
    ops = HumanOps(driver)
    for idx, op in enumerate(dir_ops):
        # use key to move
        ops.press_key(key_dict[dir_dict[op]])
        driver.implicitly_wait(10)
        time.sleep(2)
        ops.report(logger)
        try:
            nodes = driver.find_elements(By.CSS_SELECTOR, 'div h6')
            for node in nodes:
                # get latitude, longitude, power of each node
                lat, lng = node.get_attribute('lat'), node.get_attribute('lng')
                power = node.find_element(By.CSS_SELECTOR, 'div.jss56').text
                info = np.expand_dims(np.array([lat, lng, power]), axis=0)
                if infos.size == 0:
                    infos = info
                else:
                    infos = np.concatenate((infos, info), axis=0)
        except:
            pass
        driver.save_screenshot('capture_contour.png')
        driver.save_screenshot(os.path.join('captures', f'capture_{idx}.png'))
    # store results
    df = pd.DataFrame(infos, columns=['lat', 'lng', 'power'])
    df = df.drop_duplicates()
    df.to_csv(df_path, index=False)
    print(f'Saved generated dataframe to {df_path}')
    return driver

def capture_num(f):
    return int(re.findall(r'(?<=\_).+(?=\.)', f)[0])

def combine_images():
    # combine the images captured each step
    dir = 'captures'
    files = os.listdir(dir)
    files = sorted(files, key=capture_num)
    indices = np.arange(0, 24, 1).reshape(4, 6)
    for id, row in enumerate(indices[:]):
        if id % 2 == 1:
            indices[id, :] = row[::-1]
    new_img = None
    for i in range(len(files)):
        idx = indices.flatten()[i]
        img_path = os.path.join(dir, files[i])
        img = Image.open(img_path)
        img_size = img.size
        if idx == 0:
            new_img = Image.new('RGB', (6*img_size[0], 4*img_size[1]))
        new_img.paste(img, (img_size[0] * (idx%6), img_size[1] * (idx//6)))
    new_img = new_img.resize(img_size)
    new_img.save('merged_map.png', 'PNG')
    print('Saved combined image')


if __name__ == '__main__':
    driver = config()
    driver = load_and_relocate(driver)
    driver = contour_map(driver)
    combine_images()
    driver.close()
    os.remove('capture_contour.png')
    os.remove('capture_start.png')
    print('Job finished')
