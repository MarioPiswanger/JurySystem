import os
import sys
import flet as ft
from view import View, go, open_url

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from shared.database import JuryDatabase, User, Restrictions

def header():
    return ['', '', 'Username', 'E-Mail', 'Team', 'registriert', 'läuft ab', 'Berechtigung', 'gesperrt']

class UserView(View):
    def __init__(self, page: ft.Page, db, redis):
        super().__init__(page, db, redis)

        def createRows():
            return [self.userAsRow(user, editFunc, deleteFunc) for user in self.db.getAllUsers()]

        def deleteFunc(e, userId):
            user = self.db.getUser(userId)
            def yes(e):
                self.db.removeUser(userId)
                self.page.pop_dialog()
                self.table.rows = createRows()
                self.page.update()

            def no(e):
                print('cancel')
                self.page.pop_dialog()

            dlg = ft.AlertDialog(
                modal=True,
                content=ft.Text(f"Delete user '{user.username}'?"),
                actions=[
                    ft.TextButton("Yes", on_click=yes),
                    ft.TextButton("No", on_click=no),
                ],
                actions_alignment=ft.MainAxisAlignment.END)
            self.page.show_dialog(dlg)

        def editFunc(e, userId):
            print(f'edit {userId=}')
            go(self.page, f'/userEdit/{userId}')

        def addFunc(e):
            go(self.page, f'/userEdit/0')

        self.route = '/users'
        self.scroll = ft.ScrollMode.AUTO
        self.table = ft.DataTable(
                columns=[ft.DataColumn(ft.Text(h)) for h in header()],
                rows=createRows()
            )
        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr('Help'), on_click=lambda _: go(self.page, '/help')), title=ft.Text("Users"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
            ft.IconButton(ft.Icons.ADD_CIRCLE,
                    icon_color=ft.Colors.BLUE_300,
                    tooltip="Add",
                    on_click=addFunc),
            ft.Button("Home", on_click=lambda _: go(self.page, "/")),
        ]

    def userAsRow(self, user: User, editFunc: callable, deleteFunc: callable):
        cells = [
            ft.DataCell(ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color=ft.Colors.GREEN_300,
                        tooltip="Edit",
                        on_click=lambda e: editFunc(e, user.id))),
            ft.DataCell(ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_color=ft.Colors.RED_300,
                        tooltip="Delete",
                        on_click=lambda e: deleteFunc(e, user.id))),
            ft.DataCell(ft.Text(user.username)),
            ft.DataCell(ft.Text(user.email)),
            ft.DataCell(ft.Text(user.team)),
            ft.DataCell(ft.Text(str(user.registered or ''))),
            ft.DataCell(ft.Text(str(user.expires or ''))),
            ft.DataCell(ft.Text(user.restrictions.name)),
            ft.DataCell(ft.Checkbox(value=user.locked, disabled=True))
            ]
        return ft.DataRow(cells=cells)

class UserEditView(View):
    def __init__(self, page: ft.Page, db, redis, userId: int):
        super().__init__(page, db, redis)
        self.route = f'/userEdit/{userId}'
        self.scroll = ft.ScrollMode.AUTO

        createUser = userId == 0

        def update(e):
            if createUser:
                print(f'creating user')
                self.db.insertUser(nameEdit.value, passwordEdit.value, emailEdit.value, teamEdit.value, Restrictions[resitrictionsEdit.value], langEdt.value)
            else:
                print(f'saving {userId=}')
                self.db.updateUser(userId, nameEdit.value, passwordEdit.value, emailEdit.value, teamEdit.value, expiresEdit.value, Restrictions[resitrictionsEdit.value], lockedEdit.value, langEdt.value)
            go(self.page, "/users")

        def cancel(e):
            print(f'cancel {userId=}')
            go(self.page, "/users")

        print(f'get user {userId=}')
        if not createUser:
            user = self.db.getUser(userId)
            print(f'{user.username=}')
        nameEdit = ft.TextField(label="Username", value=None if createUser else user.username)
        passwordEdit = ft.TextField(label="Password", password=True, value=None if createUser else 'password')
        emailEdit = ft.TextField(label="Email", value=None if createUser else user.email)
        teamEdit = ft.TextField(label="Team", value=None if createUser else user.team)
        resitrictionsEdit = ft.Dropdown(
            label="Restrictions",
            width = 300,
            options=[ft.DropdownOption(e.name) for e in Restrictions],
            value=Restrictions.TRAINER.name if createUser else user.restrictions.name)
        langEdt = ft.Dropdown(label="Language", width=300, options=[ft.DropdownOption(l) for l in ['en', 'ge']], value='en' if createUser else user.language)
        expiresEdit = ft.TextField(label="expires", value=None if createUser or user.expires is None else str(user.expires))
        lockedEdit = ft.Checkbox(label="locked", value=False if createUser else user.locked)
        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.HELP_OUTLINE, tooltip=self.tr.tr('Help'), on_click=lambda _: go(self.page, '/help')), title=ft.Text(f'{'Create ' if createUser else 'Edit '} User'), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            nameEdit,
            passwordEdit,
            emailEdit,
            teamEdit,
            resitrictionsEdit,
            langEdt]
        if not createUser:
            self.controls += [
                expiresEdit,
                lockedEdit
            ]
        self.controls += [
            ft.Row(spacing=0, controls=
                [
                    ft.IconButton(
                        icon=ft.Icons.CHECK_CIRCLE,
                        icon_color=ft.Colors.GREEN_300,
                        tooltip="Save",
                        on_click=update),
                    ft.IconButton(
                        icon=ft.Icons.CANCEL,
                        icon_color=ft.Colors.RED_300,
                        tooltip="Cancel",
                        on_click=cancel)], scroll=ft.ScrollMode.AUTO),
            ft.Button("Home", on_click=lambda _: go(self.page, "/"))
        ]
