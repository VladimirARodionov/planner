from typing import List, Optional, Dict, Any, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    StatusSetting, PrioritySetting, DurationSetting, DurationType
)
from backend.services.auth_service import AuthService

class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.auth_service = AuthService(session)

    async def get_settings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Получить все активные настройки"""
        statuses = await self.session.execute(
            select(StatusSetting).where(StatusSetting.is_active == True)
        )
        priorities = await self.session.execute(
            select(PrioritySetting).where(PrioritySetting.is_active == True)
        )
        durations = await self.session.execute(
            select(DurationSetting).where(DurationSetting.is_active == True)
        )

        return {
            'statuses': [status.to_dict() for status in statuses.scalars()],
            'priorities': [priority.to_dict() for priority in priorities.scalars()],
            'durations': [duration.to_dict() for duration in durations.scalars()]
        }

    async def create_setting(
        self,
        user_id: str,
        setting_type: str,
        setting_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Создать новую настройку"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return None

        setting_class = self._get_setting_class(setting_type)
        if not setting_class:
            return None

        if setting_type == 'status':
            setting = StatusSetting(
                user_id=user.id,
                name=setting_data['name'],
                code=setting_data['code'],
                color=setting_data.get('color', '#808080'),
                order=setting_data.get('order', 0),
                is_active=setting_data.get('is_active', True),
                is_default=setting_data.get('is_default', False),
                is_final=setting_data.get('is_final', False)
            )
        elif setting_type == 'priority':
            setting = PrioritySetting(
                user_id=user.id,
                name=setting_data['name'],
                color=setting_data.get('color', '#808080'),
                order=setting_data.get('order', 0),
                is_active=setting_data.get('is_active', True),
                is_default=setting_data.get('is_default', False)
            )
        else:  # duration
            setting = DurationSetting(
                user_id=user.id,
                name=setting_data['name'],
                duration_type=DurationType(setting_data['type']),
                value=setting_data['value'],
                is_active=setting_data.get('is_active', True),
                is_default=setting_data.get('is_default', False)
            )

        self.session.add(setting)
        await self.session.commit()
        await self.session.refresh(setting)

        return setting.to_dict()

    async def update_setting(
        self,
        user_id: str,
        setting_type: str,
        setting_id: int,
        setting_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Обновить настройку"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return None

        setting_class = self._get_setting_class(setting_type)
        if not setting_class:
            return None

        setting = await self.session.get(setting_class, setting_id)
        if not setting or setting.user_id != user.id:
            return None

        if setting_type == 'status':
            if 'name' in setting_data:
                setting.name = setting_data['name']
            if 'code' in setting_data:
                setting.code = setting_data['code']
            if 'color' in setting_data:
                setting.color = setting_data['color']
            if 'order' in setting_data:
                setting.order = setting_data['order']
            if 'is_active' in setting_data:
                setting.is_active = setting_data['is_active']
            if 'is_default' in setting_data:
                setting.is_default = setting_data['is_default']
            if 'is_final' in setting_data:
                setting.is_final = setting_data['is_final']
        elif setting_type == 'priority':
            if 'name' in setting_data:
                setting.name = setting_data['name']
            if 'color' in setting_data:
                setting.color = setting_data['color']
            if 'order' in setting_data:
                setting.order = setting_data['order']
            if 'is_active' in setting_data:
                setting.is_active = setting_data['is_active']
            if 'is_default' in setting_data:
                setting.is_default = setting_data['is_default']
        else:  # duration
            if 'name' in setting_data:
                setting.name = setting_data['name']
            if 'type' in setting_data:
                setting.duration_type = DurationType(setting_data['type'])
            if 'value' in setting_data:
                setting.value = setting_data['value']
            if 'is_active' in setting_data:
                setting.is_active = setting_data['is_active']
            if 'is_default' in setting_data:
                setting.is_default = setting_data['is_default']

        await self.session.commit()
        await self.session.refresh(setting)

        return setting.to_dict()

    async def delete_setting(
        self,
        user_id: str,
        setting_type: str,
        setting_id: int
    ) -> bool:
        """Удалить настройку"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return False

        setting_class = self._get_setting_class(setting_type)
        if not setting_class:
            return False

        setting = await self.session.get(setting_class, setting_id)
        if not setting or setting.user_id != user.id:
            return False

        await self.session.delete(setting)
        await self.session.commit()

        return True

    def _get_setting_class(self, setting_type: str) -> Optional[Type]:
        """Получить класс настройки по типу"""
        setting_classes = {
            'status': StatusSetting,
            'priority': PrioritySetting,
            'duration': DurationSetting
        }
        return setting_classes.get(setting_type) 