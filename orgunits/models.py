"""
Copyright 2020 ООО «Верме»
"""

from django.db import models
from django.db.models.expressions import RawSQL


class OrganizationQuerySet(models.QuerySet):
    def tree_downwards(self, root_org_id):
        """
        Возвращает корневую организацию с запрашиваемым root_org_id
        и всех её детей любого уровня вложенности

        :type root_org_id: int
        """
        table_name = self.model._meta.db_table

        # в SQLite нельзя передавать названия таблиц как параметры
        # поэтому пришлось вставлять название вручную
        query = (
            "WITH RECURSIVE children (id) AS ( "
            f"SELECT {table_name}.id FROM {table_name} "
            "WHERE id = %s UNION ALL "
            f"SELECT {table_name}.id "
            f"FROM children, {table_name} "
            f"WHERE {table_name}.parent_id = children.id ) "
            f"SELECT {table_name}.id "
            f"FROM {table_name}, children WHERE children.id = {table_name}.id"
            )

        return self.filter(id__in=RawSQL(query, (root_org_id, )))

    def tree_upwards(self, child_org_id):
        """
        Возвращает корневую организацию с запрашиваемым child_org_id
        и всех её родителей любого уровня вложенности

        :type child_org_id: int
        """
        table_name = self.model._meta.db_table
        query = (
            "WITH RECURSIVE parent (id, parent_id) AS ( "
            f"SELECT {table_name}.id, {table_name}.parent_id FROM {table_name}"
            " WHERE id = %s UNION ALL "
            f"SELECT {table_name}.id, {table_name}.parent_id "
            f"FROM parent, {table_name} "
            f"WHERE {table_name}.id = parent.parent_id ) "
            f"SELECT {table_name}.id "
            f"FROM {table_name}, parent WHERE parent.id = {table_name}.id"
            )
        return self.filter(id__in=RawSQL(query, (child_org_id, )))


class Organization(models.Model):
    """ Организация """

    objects = OrganizationQuerySet.as_manager()

    name = models.CharField(
        max_length=1000, blank=False, null=False, verbose_name="Название"
    )

    code = models.CharField(
        max_length=1000, blank=False, null=False, unique=True,
        verbose_name="Код"
    )

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT,
        verbose_name="Вышестоящая организация",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Организация"
        verbose_name = "Организации"

    def parents(self):
        """
        Возвращает всех родителей любого уровня вложенности

        :rtype: django.db.models.QuerySet
        """
        return type(self).objects.tree_upwards(self.id).exclude(id=self.id)

    def children(self):
        """
        Возвращает всех детей любого уровня вложенности

        :rtype: django.db.models.QuerySet
        """
        return type(self).objects.tree_downwards(self.id).exclude(id=self.id)

    def __str__(self):
        return self.name
