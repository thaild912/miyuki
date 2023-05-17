from typing import Any, Callable
import discord
from enum import Enum
from discord._types import ClientT


class NavigationButtonId(Enum):
    PREV = "previous"
    NEXT = "next"


class NavigationButtonView(discord.ui.View):
    def __init__(self,
                 prev_callback: Callable = None,
                 next_callback: Callable = None,
                 timeout: float | int = 60.0):
        super().__init__(timeout=timeout)

        self.prev = None
        self.next = None
        self.message = None
        self.create_buttons(prev_callback=prev_callback, next_callback=next_callback)

    def create_buttons(self, prev_callback: Callable, next_callback: Callable):
        self.prev = NavigationButton(parent_view=self, style=discord.ButtonStyle.green, emoji="⬅",
                                     navigation_button_id=NavigationButtonId.PREV, callback_func=prev_callback)
        self.next = NavigationButton(parent_view=self, style=discord.ButtonStyle.green, emoji="➡",
                                     navigation_button_id=NavigationButtonId.NEXT, callback_func=next_callback)
        self.add_item(self.prev)
        self.add_item(self.next)

    async def enable_button(self, enable: list[bool]):
        # used to disable buttons when reached end of result
        for item in self.children:
            item.disabled = True
        if enable[0]:
            self.prev.disabled = False
        if enable[1]:
            self.next.disabled = False
        await self.message.edit(view=self)

    async def on_timeout(self):
        # remove all children and execute rejection callback on timeout
        await self.remove_all_children()

    async def remove_all_children(self):
        # remove all children and update view
        for item in self.children:
            self.remove_item(item)
        await self.message.edit(view=self)
        self.stop()


class NavigationButton(discord.ui.Button):
    def __init__(self,
                 parent_view: NavigationButtonView,
                 emoji: str,
                 style: discord.ButtonStyle,
                 navigation_button_id: NavigationButtonId,
                 callback_func: Callable = None):
        super().__init__(style=style, emoji=emoji)
        self.navigation_button_id = navigation_button_id
        self.parent_view = parent_view
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction[ClientT]) -> Any:
        # execute callback, let parent view know the pressed button's custom_id, remove all parent's children, execute callback
        await super().callback(interaction)
        await interaction.response.defer()
        await self.parent_view.enable_button(await self.callback_func())
