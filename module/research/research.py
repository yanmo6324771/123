import numpy as np

from module.base.timer import Timer
from module.base.utils import rgb2gray
from module.combat.assets import GET_ITEMS_1, GET_ITEMS_2, GET_ITEMS_3
from module.logger import logger
from module.research.assets import *
from module.research.project import ResearchSelector, RESEARCH_ENTRANCE, get_research_finished, ResearchProject
from module.ui.page import *
from module.ocr.ocr import Duration

OCR_DURATION = Duration(DURATION_REMAIN, letter=(255, 255, 255), threshold=64, name='DURATION_REMAIN')


class RewardResearch(ResearchSelector):
    _research_project_offset = 0
    _research_finished_index = 2
    research_project_started = None  # ResearchProject

    def ensure_research_stable(self):
        self.wait_until_stable(STABLE_CHECKER)

    def _in_research(self):
        return self.appear(RESEARCH_CHECK, offset=(20, 20))

    def _research_has_finished_at(self, index):
        """
        Args:
            index (int): Index of research project, 0 to 4

        Returns:
            bool: True if a research finished
        """
        finish = get_research_finished(self.device.image)
        return finish == index

    def research_has_finished(self):
        """
        Finished research should be auto-focused to the center, but sometimes didn't, due to an unknown game bug.
        This method will handle that.

        Returns:
            bool: True if a research finished
        """
        index = get_research_finished(self.device.image)
        if index is not None:
            logger.attr('Research_finished', index)
            self._research_finished_index = index
            return True
        else:
            return False

    def research_reset(self, skip_first_screenshot=True):
        """
        Args:
            skip_first_screenshot (bool):

        Returns:
            bool: If reset success.
        """
        if not self.appear(RESET_AVAILABLE):
            logger.info('Research reset unavailable')
            return False

        logger.info('Research reset')
        executed = False
        with self.stat.new(genre='research',
                           save=self.config.DropRecord_SaveResearch,
                           upload=self.config.DropRecord_UploadResearch) as record:
            record.add(self.device.image)

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear_then_click(RESET_AVAILABLE, interval=10):
                continue
            if self.handle_popup_confirm('RESEARCH_RESET'):
                executed = True
                continue

            # End
            if executed and self._in_research():
                self.ensure_no_info_bar(timeout=3)  # Refresh success
                self.ensure_research_stable()
                break

        self._research_project_offset = 0
        return True

    def research_select(self, priority):
        """
        Args:
            priority (list): A list of ResearchProject objects and preset strings,
                such as [object, object, object, 'reset']

        Returns:
            bool: False if have been reset
        """
        if not len(priority):
            logger.info('No research project satisfies current filter')
            return True
        for project in priority:
            # priority example: ['reset', 'shortest']
            if project == 'reset':
                if self.research_reset():
                    return False
                else:
                    continue

            if isinstance(project, str):
                # priority example: ['shortest']
                if project == 'shortest':
                    self.research_select(self.research_sort_shortest())
                elif project == 'cheapest':
                    self.research_select(self.research_sort_cheapest())
                else:
                    logger.warning(f'Unknown select method: {project}')
                return True
            else:
                # priority example: [ResearchProject, ResearchProject,]
                if self.research_project_start(project):
                    return True
                else:
                    continue

        logger.info('No research project started')
        return True

    def research_project_start(self, project, skip_first_screenshot=True):
        """
        Args:
            project (ResearchProject):
            skip_first_screenshot:

        Returns:
            bool: If start success.
        """
        logger.info(f'Research project: {project}')
        if project in self.projects:
            index = self.projects.index(project)
        else:
            logger.warning(f'The project to start: {project} is not in known projects')
            return False
        logger.info(f'Research project: {index}')
        available = False
        click_timer = Timer(10)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            max_rgb = np.max(rgb2gray(np.array(self.image_area(RESEARCH_UNAVAILABLE))))

            # Don't use interval here, RESEARCH_CHECK already appeared 5 seconds ago
            if click_timer.reached() and self.appear(RESEARCH_CHECK, offset=(20, 20)):
                i = (index - self._research_project_offset) % 5
                logger.info(f'Project offset: {self._research_project_offset}, project {index} is at {i}')
                self.device.click(RESEARCH_ENTRANCE[i])
                self._research_project_offset = (index - 2) % 5
                self.ensure_research_stable()
                click_timer.reset()
                continue
            if max_rgb > 235 and self.appear_then_click(RESEARCH_START, offset=(5, 20), interval=10):
                available = True
                continue
            if self.handle_popup_confirm('RESEARCH_START'):
                continue

            # End
            if self.appear(RESEARCH_STOP, offset=(20, 20)):
                # RESEARCH_STOP is a semi-transparent button, color will vary depending on the background.
                self.research_detail_quit()
                # self.ensure_no_info_bar(timeout=3)  # Research started
                self.research_project_started = project
                return True
            if not available and max_rgb <= 235 and self.appear(RESEARCH_UNAVAILABLE, offset=(5, 20)):
                logger.info('Not enough resources to start this project')
                self.research_detail_quit()
                self.research_project_started = None
                return False

    def research_receive(self, skip_first_screenshot=True):
        """
        Args:
            skip_first_screenshot:

        Pages:
            in: page_research, stable, with project finished.
            out: page_research

        Returns:
            bool: True if success to receive rewards.
                  False if project requirements are not satisfied.
        """
        logger.hr('Research receive', level=2)

        def get_items():
            for b in [GET_ITEMS_3, GET_ITEMS_2, GET_ITEMS_1]:
                if self.appear(b, offset=(5, 0)):
                    return b
            return None

        with self.stat.new(genre='research',
                           save=self.config.DropRecord_SaveResearch,
                           upload=self.config.DropRecord_UploadResearch) as record:
            # Take screenshots of project list
            record.add(self.device.image)

            # Click finished project, to GET_ITEMS_*
            confirm_timer = Timer(1.5, count=5)
            record_button = None
            while 1:
                if skip_first_screenshot:
                    skip_first_screenshot = False
                else:
                    self.device.screenshot()

                if self.appear(RESEARCH_CHECK, interval=10):
                    if self._research_has_finished_at(self._research_finished_index):
                        self.device.click(RESEARCH_ENTRANCE[self._research_finished_index])

                if self.appear(RESEARCH_STOP, offset=(20, 20)):
                    logger.info('The research time is up, but requirements are not satisfied')
                    self.research_project_started = None
                    self.research_detail_quit()
                    return False

                appear_button = get_items()
                if appear_button is not None:
                    if appear_button == record_button:
                        if confirm_timer.reached():
                            break
                    else:
                        logger.info(f'{appear_button} appeared')
                        record_button = appear_button
                        confirm_timer.reset()

            # Take screenshots of items
            if record:
                button = get_items()
                if button == GET_ITEMS_1 or button == GET_ITEMS_2:
                    record.add(self.device.image)
                elif button == GET_ITEMS_3:
                    self.device.sleep(1.5)
                    self.device.screenshot()
                    record.add(self.device.image)
                    self.device.swipe((0, 250), box=ITEMS_3_SWIPE.area, random_range=(-10, -10, 10, 10), padding=0)
                    self.device.sleep(2)
                    self.device.screenshot()
                    record.add(self.device.image)

        # Close GET_ITEMS_*, to project list
        self.ui_click(appear_button=get_items, click_button=GET_ITEMS_RESEARCH_SAVE, check_button=self._in_research,
                      skip_first_screenshot=True)
        return True

    def research_reward(self):
        """
        Receive research reward and start new research.
        Unable to detect research is running.

        Pages:
            in: page_research, stable.
            out: page_research, with research project information, but it's still page_research.

        Returns:
            bool: If success to receive old project and start a new project.
        """
        logger.hr('Research reward', level=1)
        if self.research_has_finished():
            success = self.research_receive()
            if not success:
                return False
        else:
            logger.info('No research has finished')

        # In JP server, if received finished project was at the 4th(mid-right) entrance,
        # positions of projects will not change while entering the 4th entrance.
        # Re-enter page_research to fix it
        if self.config.SERVER == 'jp':
            if self._research_finished_index == 3:
                self.ui_goto_main()
                self.ui_ensure_research()

        self._research_project_offset = 0

        for _ in range(2):
            logger.hr('Research select', level=1)
            self.research_detect(self.device.image)
            priority = self.research_sort_filter()
            result = self.research_select(priority)
            if result:
                break

        return True

    def research_get_remain(self):
        """
        Get remain duration of current project (the one in the middle).

        Returns:
            bool: True if success
                  False if project requirements are not satisfied.

        Pages:
            in: page_research, stable.
            out: page_research, stable.
        """
        logger.hr('Research get remain')
        self.research_detect(self.device.image)
        remain = OCR_DURATION.ocr(self.device.image)
        logger.info(f'Research project remain: {remain}')

        if remain.total_seconds() > 0:
            project = self.projects[2]
            project.duration = remain.total_seconds() / 3600
            self.research_project_started = project
            return True
        else:
            self.research_project_started = None
            return False

    def ui_ensure_research(self):
        """
        Pages:
            in: Any page
            out: page_research
        """
        self.ui_goto(page_research, skip_first_screenshot=True)
        self.ensure_research_stable()

    def run(self):
        """
        Pages:
            in: Any page
            out: page_research, with research project information, but it's still page_research.
        """
        self.ui_ensure(page_reward)
        if self.appear(RESEARCH_FINISHED) or self.appear(RESEARCH_PENDING, offset=(20, 20)):
            self.ui_ensure_research()
            success = self.research_reward()
        else:
            self.ui_ensure_research()
            success = self.research_get_remain()

        project = self.research_project_started
        if success:
            if project is not None:
                # Success to start a project
                self.config.delay_next_run(minute=float(project.duration) * 60)
            else:
                # No project satisfies current filter
                self.config.delay_next_run(server_update=True)
        else:
            # Project requirements are not satisfied
            self.config.delay_next_run(success=False)
