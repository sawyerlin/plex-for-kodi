import xbmc
import xbmcgui
import kodigui
from lib import util, image, backgroundthread
from plexnet import plexapp


class UserThumbTask(backgroundthread.Task):
    def setup(self, users, callback):
        self.users = users
        self.callback = callback
        return self

    def run(self):
        for user in self.users:
            if self.isCanceled():
                return

            thumb, back = image.getImage(user.thumb, user.id)
            self.callback(user, thumb, back)


class UserSelectWindow(kodigui.BaseWindow):
    xmlFile = 'script-plex-user_select.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    USER_LIST_ID = 101
    PIN_ENTRY_GROUP_ID = 400

    def __init__(self, *args, **kwargs):
        self.task = None
        self.selected = False
        kodigui.BaseWindow.__init__(self, *args, **kwargs)

    def onFirstInit(self):
        self.userList = kodigui.ManagedControlList(self, self.USER_LIST_ID, 6)

        self.start()

    def onAction(self, action):
        try:
            ID = action.getId()
            if 57 < ID < 68:
                if not xbmc.getCondVisibility('ControlGroup(400).HasFocus(0)'):
                    item = self.userList.getSelectedItem()
                    if not item.dataSource.protected:
                        return
                    self.setFocusId(self.PIN_ENTRY_GROUP_ID)
                self.pinEntryClicked(ID + 142)
            elif ID in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_BACKSPACE):
                if xbmc.getCondVisibility('ControlGroup(400).HasFocus(0)'):
                    self.pinEntryClicked(211)
                    return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.USER_LIST_ID:
            item = self.userList.getSelectedItem()
            if item.dataSource.isProtected:
                self.setFocusId(self.PIN_ENTRY_GROUP_ID)
            else:
                self.userSelected(item.dataSource)
        elif 200 < controlID < 212:
            self.pinEntryClicked(controlID)

    def onFocus(self, controlID):
        if controlID == self.USER_LIST_ID:
            item = self.userList.getSelectedItem()
            item.setProperty('editing.pin', '')

    def userThumbCallback(self, user, thumb, back):
        item = self.userList.getListItemByDataSource(user)
        if item:
            item.setThumbnailImage(thumb)
            item.setProperty('back.image', back)

    def start(self):
        self.setProperty('busy', '1')
        try:
            users = plexapp.ACCOUNT.homeUsers

            items = []
            for user in users:
                # thumb, back = image.getImage(user.thumb, user.id)
                # mli = kodigui.ManagedListItem(user.title, thumbnailImage=thumb, data_source=user)
                mli = kodigui.ManagedListItem(user.title, user.title[0].upper(), data_source=user)
                mli.setProperty('pin', user.title)
                # mli.setProperty('back.image', back)
                mli.setProperty('protected', user.isProtected and '1' or '')
                mli.setProperty('admin', user.isAdmin and '1' or '')
                items.append(mli)

            self.userList.addItems(items)
            self.task = UserThumbTask().setup(users, self.userThumbCallback)
            backgroundthread.BGThreader.addTask(self.task)

            self.setFocusId(self.USER_LIST_ID)
            self.setProperty('initialized', '1')
        finally:
            self.setProperty('busy', '')

    def pinEntryClicked(self, controlID):
        item = self.userList.getSelectedItem()
        if item.getProperty('editing.pin'):
            pin = item.getProperty('editing.pin')
        else:
            pin = ''

        if controlID < 210:
            pin += str(controlID - 200)
        elif controlID == 210:
            pin += '0'
        elif controlID == 211:
            pin = pin[:-1]

        pin = pin[:4]

        if pin:
            item.setProperty('pin', ' '.join(list(u"\u2022" * len(pin))))
            item.setProperty('editing.pin', pin)
            if len(pin) > 3:
                self.userSelected(item.dataSource, pin)
        else:
            item.setProperty('pin', item.dataSource.title)
            item.setProperty('editing.pin', '')

    def userSelected(self, user, pin=None):
        # xbmc.sleep(500)
        util.DEBUG_LOG('Home user selected: {0}'.format(user))

        from lib import plex
        with plex.CallbackEvent(plexapp.APP, 'account:response') as e:
            if plexapp.ACCOUNT.switchHomeUser(user.id, pin) and plexapp.ACCOUNT.switchUser:
                util.DEBUG_LOG('Waiting for user change...')
            else:
                e.close()

        self.selected = True
        self.doClose()

    def finished(self):
        if self.task:
            self.task.cancel()


def start():
    w = UserSelectWindow.open()
    selected = w.selected
    del w
    return selected
