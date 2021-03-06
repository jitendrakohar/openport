import datetime
import os
import sys
from time import sleep
import threading

import wx

from wx.lib import intctrl
from wx._core import EVT_PAINT
from wx._gdi import PaintDC


sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..', '..'))
from openport.common.share import Share
from openport.services import osinteraction
from openport.services.logger_service import get_logger
from openport.services import qr_service, image_service
from openport.gui.trayicon import OpenPortItTaskBarIcon
from openport.services.app_service import AppService
from openport.common.session import Session
from openport.services.dbhandler import DBHandler

from gui_tcp_server import GUITcpServer
from openport.apps.app_tcp_server import is_running
from openport.common.config import OpenportAppConfig
from openport.services.config_service import ConfigService

from openport.services.logger_service import set_log_level
import logging


logger = get_logger(__name__)

noColor = True
BYTES_PER_MB = 1024 * 1024

COLOR_NO_APP_RUNNING = (204, 204, 204)
COLOR_APP_ERROR = (255, 52, 0)
COLOR_OK = (236, 236, 236)


class SharesFrame(wx.Frame):
    def onClose(self, evt):
        self.Hide()

    def __init__(self, parent=None, id=-1, title='Openport - Easy and secure reverse SSH', wx_app=None, db_location=''):

        wx.Frame.__init__(self, parent, -1, title,
                          style=wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        self.wx_app = wx_app
        self.addMenuBar()
        self.rebuild()
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.os_interaction = osinteraction.getInstance()
        self.config = OpenportAppConfig()
        self.config.app = self
        self.config_service = ConfigService(self.config)
        self.app_service = AppService(self.config)
        self.db_location = db_location
        self.db_handler = DBHandler(db_location)

        port = self.config_service.get_and_save_manager_port()
        self.server = GUITcpServer('127.0.0.1', port, self.config, self.db_handler)

        if osinteraction.is_mac():
            icon_file = self.os_interaction.get_resource_path('resources/icon.icns')
            icon = wx.Icon(icon_file, wx.BITMAP_TYPE_ICON)
        else:
            icon_file = self.os_interaction.get_resource_path('resources/icon.ico')
            icon = wx.Icon(icon_file, wx.BITMAP_TYPE_ICO)

        self.SetIcon(icon)

        self.addTrayIcon()

    def initialize(self):

        self.server.run_threaded()

        shares = self.db_handler.get_active_shares()
        shares.extend(self.db_handler.get_shares_to_restart())

        shares = {x.id: x for x in shares}.values()

        for share in shares:
            self.add_share(share)
            if not is_running(share):
                self.notify_app_down(share)

        for share in shares:
            self.server.register_with_app(share)

    def showFrame(self, event):
        print "show frame"
        self.Show(True)
        self.Raise()
        self.Iconize(False)
        self.SetFocus()
        self.os_interaction.activate_app()

    def exitApp(self, event):
        self.tbicon.RemoveIcon()
#        self.tbicon.Destroy()
        self.server.stop()
        wx.Exit()
      #  os._exit(0)

    def addTrayIcon(self):
        self.tbicon = OpenPortItTaskBarIcon(self)
        self.tbicon.addItem('View shares', self.showFrame)
        self.tbicon.addItem('---', None)
        self.tbicon.addItem('Exit', self.exitApp)
        self.tbicon.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.showFrame)

    def addMenuBar(self):
        self.menubar = wx.MenuBar()
        file = wx.Menu()
        #        help = wx.Menu()
        #file.Append(101, '&New share', 'Share a new document')
        #self.Bind(wx.EVT_MENU, self.showOpenportItDialog, id=101)

        file.Append(102, '&Open Port\tCtrl+O', 'Open a new port')
        self.Bind(wx.EVT_MENU, self.show_openport_dialog, id=102)
        file.AppendSeparator()
        quit = wx.MenuItem(file, 105, '&Quit\tCtrl+Q', 'Quit the Application')
        self.Bind(wx.EVT_MENU, self.exitApp, id=105)
        file.AppendItem(quit)
        self.menubar.Append(file, '&File')
        #        menubar.Append(help, '&Help')
        self.SetMenuBar(self.menubar)

    def init_shortcuts(self):
        id_event_open = wx.NewId()
        self.Bind(wx.EVT_MENU, self.show_openport_dialog, id=id_event_open)

        id_event_quit = wx.NewId()
        self.Bind(wx.EVT_MENU, self.exitApp, id=id_event_quit)

        accelerator_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL,  ord('O'), id_event_open),
            (wx.ACCEL_CTRL,  ord('Q'), id_event_quit),
        ])
        self.SetAcceleratorTable(accelerator_tbl)

    #def showOpenportItDialog(self, event):
    #    dlg = wx.FileDialog(
    #        self, message="Choose a file to share",
    #        defaultFile="",
    #        wildcard="*",
    #        style=wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR
    #    )
    #    if dlg.ShowModal() == wx.ID_OK:
    #        paths = dlg.GetPaths()
    #        for path in paths:
    #            #self.application.startOpenportItProcess(path)
    #            pass
    #    dlg.Destroy()

    def show_openport_dialog(self, event):
        dialog = StartOpenportDialog(self)
        dialog.ShowModal()

        if dialog.GetReturnCode() == wx.ID_OK:

            def foo():
                session = Session()
                session.local_port = dialog.port_input.GetValue()
                session.http_forward = dialog.http_forward_checkbox.GetValue()
                p = self.app_service.start_openport_process_from_session(session)
                #self.os_interaction.print_output_continuously_threaded(p)
            wx.CallAfter(foo)

    def rebuild(self):
        self.share_panels = {}
        self.frame_sizer = wx.BoxSizer(wx.VERTICAL)

        #self.account_panel = wx.Panel(self, style=wx.BORDER_NONE)
        #self.frame_sizer.Add(self.account_panel, 0, wx.EXPAND | wx.ALL, 0)
        #self.account_panel_sizer = wx.BoxSizer(wx.VERTICAL)
#
        #self.account_amount_text = wx.StaticText(self.account_panel, -1, 'Openport - Easy and secure reverse SSH')
        #self.account_amount_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        #self.account_amount_text.SetSize(self.account_amount_text.GetBestSize())
        #self.account_panel_sizer.Add(self.account_amount_text, 0, wx.EXPAND | wx.ALL)
#
        #self.account_reset_text = wx.StaticText(self.account_panel, -1, ' ')
        #self.account_reset_text.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL))
        #self.account_reset_text.SetSize(self.account_reset_text.GetBestSize())
        #self.account_panel_sizer.Add(self.account_reset_text, 0, wx.EXPAND | wx.ALL)
        #self.account_panel.SetSizer(self.account_panel_sizer)
        #self.account_panel.SetMinSize((400, 50))
#
        #self.account_panel.Layout()
        #self.Layout()

        self.scrolling_window = wx.ScrolledWindow(self)
        if not noColor:
            self.scrolling_window.SetBackgroundColour('green')
        self.SetSize((500, 300))

        self.scrolling_window.SetScrollRate(8, 8)
        self.scrolling_window.EnableScrolling(True, True)
        self.scrolling_window_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scrolling_window_sizer.Add(self.scroll_panel_sizer, 1, wx.EXPAND)
        self.scrolling_window.SetSizer(self.scrolling_window_sizer)

        self.frame_sizer.Add(self.scrolling_window, 1, wx.EXPAND | wx.ALL)

        self.scrolling_window.SetFocus()
        self.Bind(wx.EVT_SET_FOCUS, self.onFocus)

        self.scrolling_window.Layout()
        self.SetSizer(self.frame_sizer)
        self.Layout()
        self.init_shortcuts()
        self.show_no_shares_message()

    def show_no_shares_message(self):
        logger.debug('showing no shares message')
        self.no_shares_text_panel = wx.Panel(self.scrolling_window, id=2, style=wx.BORDER_NONE)

        self.scrolling_window_sizer.Add(self.no_shares_text_panel, 0, wx.EXPAND, 0)
        no_shares_text_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        top_panel = wx.Panel(self.no_shares_text_panel)
        top_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        text_panel = wx.Panel(top_panel)
        text_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        filename_text = wx.StaticText(text_panel, -1, 'You have no active sessions. Start a session by using the "File" menu.')
        filename_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        filename_text.SetSize(filename_text.GetBestSize())
        text_panel_sizer.Add(filename_text, 1, wx.EXPAND | wx.ALL)

        text_panel.SetSizer(text_panel_sizer)
        top_panel_sizer.Add(text_panel, 1, wx.EXPAND)

        top_panel.SetSizer(top_panel_sizer)
        no_shares_text_panel_sizer.Add(top_panel, 0, wx.EXPAND)


        self.no_shares_text_panel.SetSizer(no_shares_text_panel_sizer)

        self.no_shares_text_panel.GetParent().Layout()
        self.frame_sizer.Layout()

    def hide_no_shares_message(self):
        if self.no_shares_text_panel:
            self.no_shares_text_panel.Destroy()

    def update_account(self,
                       bytes_this_month=-1,
                       next_counter_reset_time=datetime.datetime.now(),
                       max_bytes=-1,
    ):
        self.account_amount_text.SetLabel(
            '%sMB / %sMB used' % (bytes_this_month / BYTES_PER_MB, max_bytes / BYTES_PER_MB ))
        self.account_reset_text.SetLabel('Counters will be reset on %s' % next_counter_reset_time)

    def onFocus(self, event):
        self.scrolling_window.SetFocus()

    def add_share_after(self, share):
        wx.CallAfter(self.add_share, share)

    def add_share(self, share):
        logger.debug('add share')
        if share.id in self.share_panels:
            self.notify_success(share)
            return

        self.hide_no_shares_message()
        if isinstance(share, Share):
            filename = share.filePath
        else:
            filename = str(share.local_port)

        share_panel = wx.Panel(self.scrolling_window, id=2, style=wx.BORDER_RAISED)
        self.share_panels[share.id] = share_panel

        self.scrolling_window_sizer.Add(share_panel, 0, wx.EXPAND, 0)
        share_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        top_panel = wx.Panel(share_panel)
        top_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        text_panel = wx.Panel(top_panel)
        text_panel_sizer = wx.BoxSizer(wx.VERTICAL)

        filename_text = wx.StaticText(text_panel, -1, os.path.basename(filename))
        filename_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        filename_text.SetSize(filename_text.GetBestSize())
        text_panel_sizer.Add(filename_text, 1, wx.EXPAND | wx.ALL)

        link_text = wx.StaticText(text_panel, -1, share.get_link())
        link_text.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD))
        link_text.SetSize(link_text.GetBestSize())
        text_panel_sizer.Add(link_text, 1, wx.EXPAND | wx.ALL)

        text_panel.SetSizer(text_panel_sizer)
        top_panel_sizer.Add(text_panel, 1, wx.EXPAND)

        button_panel = wx.Panel(top_panel)
        button_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_panel.SetSizer(button_panel_sizer)
        if not noColor:
            button_panel.SetBackgroundColour((255, 52, 0))
        top_panel_sizer.Add(button_panel, 0, wx.ALIGN_LEFT | wx.EXPAND)

        def restart_share(evt):
            def foo():
                if not share.restart_command:
                    share.restart_command = self.app_service.get_restart_command(share,
                                                                                 self.db_location,
                                                                                 self.config.verbose,
                                                                                 self.config.openport_address)
                full_command = self.os_interaction.get_full_restart_command(share)
               # self.os_interaction.spawn_daemon(full_command)
                p = self.os_interaction.start_process(full_command)
                #self.os_interaction.print_output_continuously_threaded(p)
                self.remove_share(share)
            wx.CallAfter(foo)

        restart_button = wx.Button(button_panel, -1, label="Restart")
        restart_button.Bind(wx.EVT_BUTTON, restart_share)
        button_panel_sizer.Add(restart_button, 0, wx.EXPAND | wx.ALL)
        restart_button.Hide()
        share_panel.restart_button = restart_button

        def copy_link(evt):
            self.os_interaction.copy_to_clipboard(share.get_link())

        copy_link_button = wx.Button(button_panel, -1, label="Copy link")
        copy_link_button.Bind(wx.EVT_BUTTON, copy_link)
        button_panel_sizer.Add(copy_link_button, 0, wx.EXPAND | wx.ALL)

        if share.open_port_for_ip_link:
            def copy_open_port_for_ip_link(evt):
                self.os_interaction.copy_to_clipboard(share.open_port_for_ip_link)

            copy_open_port_for_ip_link_button = wx.Button(button_panel, -1, label="Copy open-for-ip link")
            copy_open_port_for_ip_link_button.Bind(wx.EVT_BUTTON, copy_open_port_for_ip_link)
            button_panel_sizer.Add(copy_open_port_for_ip_link_button, 0, wx.EXPAND | wx.ALL)

        def send_stop_share(evt):
            # self.add_share(share)
            # return
            logger.info("stopping %s" % share.id)
            s = self.db_handler.get_share(share.id)
            if s and s.app_management_port:
                self.notify_app_down(s)
                self.server.app_communicate(s, 'exit', {'id': share.id})

            def remove_killed_share():
                while is_running(s):
                    sleep(1)
                wx.CallAfter(self.remove_share, share)
                self.db_handler.stop_share(share, restart=False)
            t = threading.Thread(target=remove_killed_share)
            t.setDaemon(True)
            t.start()

        stop_sharing_button = wx.Button(button_panel, -1, label="Stop")
        stop_sharing_button.Bind(wx.EVT_BUTTON, send_stop_share)
        button_panel_sizer.Add(stop_sharing_button, 0, wx.EXPAND | wx.ALL)

        def show_qr_evt(evt):
            self.show_qr('%s -> localhost:%s' % (share.get_link(), share.local_port), share.get_link())

        qr_button = wx.Button(button_panel, -1, label="Show QR")
        qr_button.Bind(wx.EVT_BUTTON, show_qr_evt)
        button_panel_sizer.Add(qr_button, 0, wx.EXPAND | wx.ALL)

        top_panel.SetSizer(top_panel_sizer)
        share_panel_sizer.Add(top_panel, 0, wx.EXPAND)

        dir_text = wx.StaticText(share_panel, -1, os.path.dirname(filename))
        dir_text.SetSize(dir_text.GetBestSize())
        share_panel_sizer.Add(dir_text, 0, wx.EXPAND | wx.ALL)

        share_panel.SetSizer(share_panel_sizer)

        share_panel.GetParent().Layout()
        self.frame_sizer.Layout()

        shares = self.db_handler.get_shares_to_restart() + self.db_handler.get_active_shares()
        for s in shares:
            if s.local_port != share.local_port:
                continue
            if s.id == share.id:
                continue
            if s.id not in self.share_panels:
                continue
            if not s.active:
                self.remove_share(s)

    def show_qr(self, title, data):
        pil_img = qr_service.get_qr_image(data)
        wx_img = image_service.PilImageToWxImage(pil_img)
        qr_frame = QrFrame(None, -1, title)
        qr_frame.add_img(wx_img)
        qr_frame.Show(True)

    def notify_error(self, share):
        logger.debug('notify_error')
        if share.id in self.share_panels:
            share_panel = self.share_panels[share.id]
            wx.CallAfter(share_panel.SetBackgroundColour, COLOR_APP_ERROR)
            wx.CallAfter(share_panel.Refresh)
        else:
            logger.debug('share not found while notifying error')

    def notify_app_down(self, share):
        logger.debug('notify_app_down')
        if share.id in self.share_panels:
            share_panel = self.share_panels[share.id]
            share_panel.SetBackgroundColour(COLOR_NO_APP_RUNNING)
            share_panel.restart_button.Show()
            share_panel.Refresh()
            self.frame_sizer.Layout()
        else:
            logger.debug('share not found while notifying app down')

    def notify_success(self, share):
        logger.debug('notify_success')
        if share.id in self.share_panels:
            share_panel = self.share_panels[share.id]

            share_panel.SetBackgroundColour(COLOR_OK)
            share_panel.restart_button.Hide()
            share_panel.Refresh()
            self.frame_sizer.Layout()
        else:
            logger.debug('share not found while notifying success')

    def remove_share(self, share):
        logger.debug('remove_share %s' % share.local_port)
        if share.id in self.share_panels:
            def do_it():
                share_panel = self.share_panels[share.id]
                self.scrolling_window.RemoveChild(share_panel)
                self.scrolling_window_sizer.Remove(share_panel)
                share_panel.Destroy()
                self.share_panels.pop(share.id)
                self.scrolling_window.Layout()
                self.scrolling_window.Refresh()
                self.Layout()
                if len(self.share_panels) == 0:
                    self.show_no_shares_message()
            wx.CallAfter(do_it)
        else:
            logger.debug('share not found while removing')


class QrFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title)  #, title,
        #style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE|wx.NO_BORDER|
        #     wx.FRAME_TOOL_WINDOW|wx.STAY_ON_TOP)

    def add_img(self, wx_img):
        self.frame_sizer = wx.BoxSizer(wx.VERTICAL)

        self.img_panel = ImagePanel(self, -1)
        self.img_panel.display(wx_img)
        self.frame_sizer.Add(self.img_panel, 0, wx.EXPAND | wx.ALL, 0)
        self.img_panel.Layout()
        self.SetSize((470, 480))
        self.Layout()


class ImagePanel(wx.Panel):
    def __init__(self, parent, id):
        wx.Panel.__init__(self, parent, id)
        self.image = None
        EVT_PAINT(self, self.OnPaint)

    def display(self, image):
        self.image = image
        self.Refresh(True)

    def OnPaint(self, evt):
        dc = PaintDC(self)
        if self.image:
            dc.DrawBitmap(self.image.ConvertToBitmap(), 0, 0)


class StartOpenportDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        super(StartOpenportDialog, self).__init__(*args, **kw)

        self.init_UI()
        self.SetSize((250, 130))
        self.SetTitle('Open a port')

    def init_UI(self):

        pnl = wx.Panel(self)
        pnl_sizer = wx.BoxSizer(wx.VERTICAL)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(wx.StaticText(pnl, label='Port'))
        self.port_input = intctrl.IntCtrl(pnl, min=1, max=2 ** 16, value=8080)
        hbox1.Add(self.port_input)
        pnl_sizer.Add(hbox1)

        self.http_forward_checkbox = wx.CheckBox(pnl, label='HTTP Forward')
        pnl_sizer.Add(self.http_forward_checkbox)

        pnl.SetSizer(pnl_sizer)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='Start')
        closeButton = wx.Button(self, label='Cancel')
        hbox2.Add(okButton)
        hbox2.Add(closeButton, flag=wx.LEFT, border=5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(pnl, proportion=1,
            flag=wx.ALL|wx.EXPAND, border=5)
        vbox.Add(hbox2,
            flag=wx.ALIGN_CENTER|wx.TOP | wx.BOTTOM, border=10)

        self.SetSizer(vbox)

        okButton.Bind(wx.EVT_BUTTON, self.on_ok)
        closeButton.Bind(wx.EVT_BUTTON, self.OnClose)

    def OnClose(self, e):
        self.Destroy()
        self.EndModal(wx.ID_CANCEL)

    def on_ok(self, e):
        self.Destroy()
        self.EndModal(wx.ID_OK)


if __name__ == '__main__':
    set_log_level(logging.DEBUG)
    app = wx.App()
    frame = SharesFrame()
    frame.initialize()
    frame.Show(True)

    app.MainLoop()