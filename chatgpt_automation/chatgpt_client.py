'''Class definition for ChatGPT_Client'''

import os
import logging
import time
from datetime import datetime
import undetected_chromedriver as uc

# from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions as Exceptions

from .helpers import detect_chrome_version

import asyncio

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    level=logging.WARNING
)

class ChatGPT_Client:
    '''ChatGPT_Client class to interact with ChatGPT'''

    login_xq    = '//button[//div[text()="Log in"]]'
    continue_xq = '//button[text()="Continue"]'
    tutorial_xq = '//div[contains(text(), "Okay, let’s go")]'
    button_tq   = 'button'
    done_xq     = '//button[//div[text()="Done"]]'

    menu_xq     = '//button[contains(@id, "headlessui-menu-button")]'
    custom_xq   = '//a[contains(text(), "Custom instructions")]'
    enable_xq   = '//span[@data-state="unchecked"]'
    disable_xq   = '//span[@data-state="checked"]'
    custom_textarea_xq = '//textarea[@type="button"]'
    custom_save_xq = '//div[contains(text(), "Save")]'

    chatbox_cq  = 'text-base'
    wait_cq     = 'text-2xl'
    reset_xq    = '//a[//span[text()="New Chat"]]'
    regen_xq    = '//div[text()="Regenerate"]'
    textarea_tq = 'textarea'
    textarea_iq = 'prompt-textarea'
    gpt_xq    = '//span[text()="{}"]'

    username = None
    password = None
    locals = None
    options = None
    response_timeout = 600
    closed = False
    challenge = False
    login_failed = False

    def __init__(
        self,
        username :str = '',
        password :str = '',
        headless :bool = True,
        cold_start :bool = False,
        incognito :bool = False,
        driver_executable_path :str =None,
        driver_arguments : list = None,
        driver_version: int = None,
        verbose :bool = False
    ):
        if username or password:
            logging.warning(
                "The usage of username and password parameters are deprecated and will be removed in near feature."
                "Please adjust your environment variables to pass username and password."
            )

        self.username = username = username or os.environ.get('OPENAI_UNAME')
        self.password = password = password or os.environ.get('OPENAI_PWD')

        if not username:
            logging.error('Either provide username or set the environment variable "OPENAI_UNAME"')
            return

        if not password:
            logging.error('Either provide password or set the environment variable "OPENAI_PWD"')
            return

        if verbose:
            logging.getLogger().setLevel(logging.INFO)
            logging.info('Verbose mode active')
        self.locals = locals()

        self.goLogin()

    def goLogin(self):
        self.closed = False
        self.challenge = False
        self.login_failed = False
        options = uc.ChromeOptions()
        if self.locals['incognito']:
            options.add_argument('--incognito')
        # if headless:
        #     options.add_argument('--headless')
        options.headless = False
        if self.locals['driver_arguments']:
            for _arg in self.locals['driver_arguments']:
                options.add_argument(_arg)
        logging.info('Loading undetected Chrome')

        self.browser = uc.Chrome(
            driver_executable_path=self.locals['driver_executable_path'],
            options=options,
            headless=self.locals['headless'],
            version_main=detect_chrome_version(self.locals['driver_version']),
            log_level=10,
        )
        self.browser.set_page_load_timeout(15)
        logging.info('Loaded Undetected chrome')
        logging.info('Opening chatgpt')
        self.browser.get('https://chat.openai.com/auth/login?next=/chat')
        self.browser.execute_script(
            f"window.localStorage.setItem('oai/apps/hasSeenOnboarding/chat', {datetime.today().strftime('%Y-%m-%d')});"
        )

        if not self.locals['cold_start']:
            self.pass_verification()
            self.login(self.username, self.password)
        # if self.browser.find_elements(By.CSS_SELECTOR, '#error-element-password'):
        #     self.login_failed = True
        #     self.closed = True
        #     self.browser.quit()
        logging.info('ChatGPT is ready to interact')

    def find_or_fail(self, by, query, return_elements=False, fail_ok=False):
        """Finds a list of elements given query, if none of the items exists, throws an error

        Args:
            by (selenium.webdriver.common.by.By): The method used to locate the element.
            query (str): The query string to locate the element.

        Returns:
            selenium.webdriver.remote.webelement.WebElement: Web element or None if not found.
        """
        dom_element = self.browser.find_elements(by, query)
        if not dom_element:
            if not fail_ok:
                logging.error(f'{query} is not located. Please raise an issue with verbose=True')
            return None

        logging.debug(f'{query} is located.')
        if return_elements:
            return dom_element
        else:
            return dom_element[0]

    def pass_verification(self):
        '''
        Performs the verification process on the page if challenge is present.

        This function checks if the login page is displayed in the browser.
        In that case, it looks for the verification button.
        This process is repeated until the login page is no longer displayed.

        Returns:
            None
        '''
        while self.check_login_page():
            verify_button = self.browser.find_elements(By.ID, 'challenge-stage')
            if len(verify_button):
                try:
                    verify_button[0].click()
                    logging.info('Clicked verification button')
                except Exceptions.ElementNotInteractableException:
                    logging.info('Verification button is not present or clickable')
            time.sleep(1)
        return

    def check_login_page(self):
        '''
        Checks if the login page is displayed in the browser.

        Returns:
            bool: True if the login page is not present, False otherwise.
        '''
        login_button = self.browser.find_elements(By.XPATH, self.login_xq)
        return len(login_button) == 0

    def login(self, username :str, password :str):
        '''
        Performs the login process with the provided username and password.

        This function operates on the login page.
        It finds and clicks the login button,
        fills in the email and password textboxes

        Args:
            username (str): The username to be entered.
            password (str): The password to be entered.

        Returns:
            None
        '''

        # Find login button, click it
        login_button = self.sleepy_find_element(By.XPATH, self.login_xq)
        login_button.click()
        logging.info('Clicked login button')
        time.sleep(1)

        # Find email textbox, enter e-mail
        email_box = self.sleepy_find_element(By.ID, 'username')
        email_box.send_keys(username)
        logging.info('Filled email box')

        # Click continue
        continue_button = self.sleepy_find_element(By.XPATH, self.continue_xq)
        continue_button.click()
        time.sleep(1)
        logging.info('Clicked continue button')

        # Find password textbox, enter password
        pass_box = self.sleepy_find_element(By.ID, 'password')
        pass_box.send_keys(password)
        logging.info('Filled password box')
        # Click continue
        pass_box.send_keys(Keys.ENTER)
        time.sleep(1)
        logging.info('Logged in')

        try:
            # Pass introduction
            next_button = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.XPATH, self.tutorial_xq))
            ).click()
            #next_button.find_elements(By.TAG_NAME, self.button_tq)[0].click()

            logging.info('Info screen passed')
        except Exceptions.TimeoutException:
            logging.info('Info screen skipped')
        except Exception as exp:
            logging.error(f'Something unexpected happened: {exp}')

    def sleepy_find_element(self, by, query, attempt_count :int =20, sleep_duration :int =1):
        '''
        Finds the web element using the locator and query.

        This function attempts to find the element multiple times with a specified
        sleep duration between attempts. If the element is found, the function returns the element.

        Args:
            by (selenium.webdriver.common.by.By): The method used to locate the element.
            query (str): The query string to locate the element.
            attempt_count (int, optional): The number of attempts to find the element. Default: 20.
            sleep_duration (int, optional): The duration to sleep between attempts. Default: 1.

        Returns:
            selenium.webdriver.remote.webelement.WebElement: Web element or None if not found.
        '''
        for _count in range(attempt_count):
            item = self.browser.find_elements(by, query)
            if len(item) > 0:
                item = item[0]
                logging.info(f'Element {query} has found')
                break
            logging.info(f'Element {query} is not present, attempt: {_count+1}')
            time.sleep(sleep_duration)
        return item

    def wait_until_disappear(self, by, query, timeout_duration=30):
        '''
        Waits until the specified web element disappears from the page.

        This function continuously checks for the presence of a web element.
        It waits until the element is no longer present on the page.
        Once the element has disappeared, the function returns.

        Args:
            by (selenium.webdriver.common.by.By): The method used to locate the element.
            query (str): The query string to locate the element.
            timeout_duration (int, optional): The total wait time before the timeout exception. Default: 15.

        Returns:
            None
        '''
        logging.info(f'Waiting element {query} to disappear.')
        try:
            WebDriverWait(
                self.browser,
                timeout_duration
            ).until_not(
                EC.presence_of_element_located((by, query))
            )
            logging.info(f'Element {query} disappeared.')
        except Exceptions.TimeoutException:
            logging.info(f'Element {query} still here, something is wrong.')
        return

    def wait_until(self, by, query, timeout=600):
        try:
            WebDriverWait(
                self.browser,
                timeout
            ).until(EC.presence_of_element_located(
            (by, query)))
            logging.info(f'Element {query} disappeared.')
        except Exceptions.TimeoutException:
            logging.info(f'Element {query} still here, something is wrong.')
        return

    def wait_result(self, wait):

        logging.info('Message sent, waiting for response')
        wait.until_not(
            EC.presence_of_element_located((By.CLASS_NAME, 'result-streaming'))
        )

        self.wait_until_disappear(By.CLASS_NAME, self.wait_cq)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button span[data-state="closed"]')))
    def interact(self, question : str):
        '''
        Sends a question and retrieves the answer from the ChatGPT system.

        This function interacts with the ChatGPT.
        It takes the question as input and sends it to the system.
        The question may contain multiple lines separated by '\n'. 
        In this case, the function simulates pressing SHIFT+ENTER for each line.

        After sending the question, the function waits for the answer.
        Once the response is ready, the response is returned.

        Args:
            question (str): The interaction text.

        Returns:
            str: The generated answer.
        '''

        if self.browser.find_elements(By.CSS_SELECTOR, '#enforcement-container .active iframe') or self.browser.find_elements(By.CSS_SELECTOR, 'iframe.show[title="Verification challenge"]'):
            self.challenge = True
            self.browser.quit()
            raise RuntimeError('Cloudflare challenge!')
            return
        
        # Wait for the element to disappear using WebDriverWait
        wait =  WebDriverWait(self.browser, self.response_timeout)
        self.wait_result(wait)

        text_area = self.browser.find_elements(By.TAG_NAME, self.textarea_tq)
        if not text_area:
            logging.info('Unable to locate text area tag. Switching to ID search')
            text_area = self.browser.find_elements(By.ID, self.textarea_iq)
        
        if not text_area:

            self.browser.execute_script("""
                function deleteAllCookies() {
                    const cookies = document.cookie.split(";");

                    for (let i = 0; i < cookies.length; i++) {
                        const cookie = cookies[i];
                        const eqPos = cookie.indexOf("=");
                        const name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
                        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT";
                    }
                }
                deleteAllCookies();
            """)
            self.closed = True
            self.browser.quit()
            # return
            # self.goLogin()
            # return self.interact(question=question)
            raise RuntimeError('Unable to find the text prompt area. Please raise an issue with verbose=True')
            return
        text_area_e = text_area[0]
        text_area_e.send_keys('')
        self.browser.execute_script(f'document.getElementById("{self.textarea_iq}").value="";')

        # for each_line in question.split('\n'):
        #     text_area_e.send_keys(each_line)
        #     text_area_e.send_keys(Keys.SHIFT + Keys.ENTER)
        # text_area_e.send_keys(Keys.RETURN)
        self.browser.execute_script('arguments[0].value=arguments[1];arguments[0].focus()', text_area[0], question)
        text_area_e.send_keys(Keys.SHIFT + Keys.ENTER)
        text_area_e.send_keys(Keys.RETURN)

        #error:
        asyncio.run(self.check_error())
        self.wait_result(wait)

        try:
            unknow_policy = self.browser.find_elements(By.CSS_SELECTOR, '.fixed button.btn.relative.btn-neutral')
            if unknow_policy:
                unknow_policy[0].click()
                time.sleep(1)
                return question
        except:
            print('error unknow_policy')

        answer = self.browser.find_elements(By.CLASS_NAME, self.chatbox_cq)[-1]


        logging.info('Answer is ready')
        return answer.text

    async def check_error(self):
        await asyncio.sleep(2)
        if self.browser.find_elements(By.CSS_SELECTOR, '.flex-col.items-start.gap-3.whitespace-pre-wrap.break-words.text-red-500') or not self.browser.find_elements(By.TAG_NAME, self.textarea_tq):
            self.closed = True
            self.browser.quit()
            x=1/0
            raise RuntimeError('Message errors!')
        
    def reset_thread(self):
        '''Function to close the current thread and start new one'''
        self.browser.find_element(By.XPATH, self.reset_xq).click()
        logging.info('New thread is ready')

    def regenerate_response(self):
        '''
        Closes the current thread and starts a new one.

        Args:
            None

        Returns:
            None
        '''
        try:
            regen_button = self.browser.find_element(By.XPATH, self.regen_xq)
            regen_button.click()
            logging.info('Clicked regenerate button')
            self.wait_until_disappear(By.CLASS_NAME, self.wait_cq)
            answer = self.browser.find_elements(By.CLASS_NAME, self.chatbox_cq)[-1]
            logging.info('New answer is ready')
        except Exceptions.NoSuchElementException:
            logging.error('Regenerate button is not present')
        return answer

    def switch_model(self, model_name : str):
        '''
        Switch the model for ChatGPT+ users.

        Args:
            model_name: str = The name of the model, either GPT-3.5 or GPT-4

        Returns:
            bool: True on success, False on fail
        '''
        if model_name in ['GPT-3.5', 'GPT-4']:
            logging.info(f'Switching model to {model_name}')
            try:
                self.browser.find_element(By.XPATH, self.gpt_xq.format(model_name)).click()
                return True
            except Exceptions.NoSuchElementException:
                logging.error('Button is not present')
        return False

    def set_custom_instruction(self, mode: str, instruction: str):
        """Sets custom instructions

        Args:
            mode (str): Either 'extra_information' or 'modulation'. Check openai help pages for more information.
            instruction (str): _description_
        """
        menu_button = self.find_or_fail(By.XPATH, self.menu_xq)
        menu_button.click()
        custom_button = self.find_or_fail(By.XPATH, self.custom_xq)
        custom_button.click()
        enable_button = self.find_or_fail(By.XPATH, self.enable_xq)
        if enable_button:
            enable_button.click()
        # If custom instructions are already enabled, we need to verify that.
        else:
            logging.debug('Enable button has not found, checking if it is already enabled')
            disable_button = self.find_or_fail(By.XPATH, self.disable_xq)
            if disable_button:
                logging.debug('Custom instructions are already enabled.')

        text_areas = self.find_or_fail(By.XPATH, self.custom_textarea_xq, return_elements=True)
        text_area = text_areas[{
            'extra_information' : 0,
            'modulation' : 1
        }[mode]]

        text_area.send_keys(Keys.CONTROL + "a")
        time.sleep(0.1)
        text_area.send_keys(Keys.DELETE)
        time.sleep(0.1)
        text_area.send_keys(instruction)

        logging.debug(f'Custom instruction-{mode} has provided')

        save_button = self.find_or_fail(By.XPATH, self.custom_save_xq)
        save_button.click()
        return

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    args = parser.parse_args()

    chatgpt = ChatGPT_Client(args.username, args.password)
    result = chatgpt.interact('Hello, how are you today')
    print(result)
