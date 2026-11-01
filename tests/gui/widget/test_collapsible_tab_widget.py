# coding: utf-8

import pytest
from PySide6.QtWidgets import QWidget

from paintjob_designer.gui.widget.collapsible_tab_widget import CollapsibleTabWidget


@pytest.fixture
def tabs(qapp):
    widget = CollapsibleTabWidget()
    widget.first = QWidget()
    widget.second = QWidget()
    widget.third = QWidget()
    widget.addTab(widget.first, "First")
    widget.addTab(widget.second, "Second")
    widget.addTab(widget.third, "Third")
    return widget


class TestSetPageVisible:

    def test_hides_and_shows_the_tab(self, tabs):
        tabs.set_page_visible(tabs.third, False)
        assert not tabs.isTabVisible(tabs.indexOf(tabs.third))

        tabs.set_page_visible(tabs.third, True)
        assert tabs.isTabVisible(tabs.indexOf(tabs.third))

    def test_hiding_the_open_page_moves_to_a_visible_one(self, tabs):
        tabs.setCurrentWidget(tabs.third)

        tabs.set_page_visible(tabs.third, False)

        assert tabs.currentWidget() is not tabs.third
        assert tabs.isTabVisible(tabs.currentIndex())

    def test_open_page_reopens_when_it_comes_back(self, tabs):
        tabs.setCurrentWidget(tabs.third)

        tabs.set_page_visible(tabs.third, False)
        tabs.set_page_visible(tabs.third, True)

        assert tabs.currentWidget() is tabs.third

    def test_a_page_that_was_not_open_does_not_steal_focus_when_shown(self, tabs):
        tabs.setCurrentWidget(tabs.first)

        tabs.set_page_visible(tabs.third, False)
        tabs.set_page_visible(tabs.third, True)

        assert tabs.currentWidget() is tabs.first

    def test_clicking_another_tab_cancels_the_reopen(self, tabs):
        tabs.setCurrentWidget(tabs.third)
        tabs.set_page_visible(tabs.third, False)

        tabs.tabBarClicked.emit(tabs.indexOf(tabs.first))
        tabs.set_page_visible(tabs.third, True)

        assert tabs.currentWidget() is not tabs.third

    def test_repeating_the_same_state_keeps_the_reopen(self, tabs):
        tabs.setCurrentWidget(tabs.third)

        tabs.set_page_visible(tabs.third, False)
        tabs.set_page_visible(tabs.third, False)
        tabs.set_page_visible(tabs.third, True)

        assert tabs.currentWidget() is tabs.third
