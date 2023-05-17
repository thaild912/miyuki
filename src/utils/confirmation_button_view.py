from typing import Any, Callable
import discord
from enum import Enum
from discord._types import ClientT


class ConfirmationType(Enum):
    DELETE = 1
    OVERWRITE = 2


class ConfirmationButtonId(Enum):
    CONFIRM = "confirm"
    REJECT = "reject"


class ConfirmationButtonView(discord.ui.View):
    def __init__(self,
                 author: discord.Member,
                 confirmation_type: ConfirmationType,
                 confirm_callback: Callable = None,
                 reject_callback: Callable = None,
                 timeout: float | int = 30.0):
        super().__init__(timeout=timeout)

        self.author = author
        self.message = None
        self.reject_callback = reject_callback
        self.is_done = False

        if confirmation_type == ConfirmationType.DELETE:
            confirm_label = "Delete"
            reject_label = "Do not delete"
        elif confirmation_type == ConfirmationType.OVERWRITE:
            confirm_label = "Overwrite"
            reject_label = "Keep the old one"

        self.create_buttons(confirm_label, reject_label, confirm_callback, reject_callback)

    async def interaction_check(self,
                                interaction: discord.Interaction,
                                /) -> bool:
        # only allow ctx author to interact with the button
        return interaction.user.id == self.author.id

    def create_buttons(self,
                       confirm_label: str,
                       reject_label: str,
                       confirm_callback: Callable,
                       reject_callback: Callable):
        confirm_button = ConfirmationButton(parent_view=self, label=confirm_label, style=discord.ButtonStyle.green,
                                            confirmation_button_id=ConfirmationButtonId.CONFIRM, callback_func=confirm_callback)
        reject_button = ConfirmationButton(parent_view=self, label=reject_label, style=discord.ButtonStyle.red,
                                           confirmation_button_id=ConfirmationButtonId.REJECT, callback_func=reject_callback)
        self.add_item(confirm_button)
        self.add_item(reject_button)

    async def on_timeout(self):
        # remove all children and execute rejection callback on timeout
        if not self.is_done:
            await self.remove_all_children()
            if self.reject_callback is not None:
                await self.reject_callback()

    async def remove_all_children(self):
        # remove all children and update view
        for item in self.children:
            self.remove_item(item)
        await self.message.edit(view=self)
        self.stop()


class ConfirmationButton(discord.ui.Button):
    def __init__(self,
                 parent_view: ConfirmationButtonView,
                 label: str,
                 style: discord.ButtonStyle,
                 confirmation_button_id: ConfirmationButtonId,
                 callback_func: Callable):
        super().__init__(label=label, style=style)
        self.confirmation_button_id = confirmation_button_id
        self.parent_view = parent_view
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction[ClientT]) -> Any:
        # execute callback, let parent view know the pressed button's custom_id, remove all parent's children, execute callback
        await super().callback(interaction)
        await interaction.response.defer()
        await self.parent_view.remove_all_children()
        await self.callback_func()
        self.parent_view.is_done = True
