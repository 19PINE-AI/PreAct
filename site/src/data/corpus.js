// Real compiled programs from PreAct's corpus (rag_db_warm_baseline_20260425).
// Each is the actual state machine compiled from a successful run on a benchmark task.
// Verification predicates and actions are shown verbatim (long package prefixes trimmed).

export const CORPUS = [
  {
    "task": "Add the following songs, in order, City of Stars, Dreamer's Awake, Moonlight Sonata, Echoes of Silence, Forever Young to my playing queue in Retro music.",
    "app": "code.name.monkey.retromusic",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "retro_music_open",
        "desc": "Retro Music app main screen with bottom navigation visible",
        "verify": "resource_id=code.name.monkey.retromusic:id/action_song"
      },
      {
        "id": "songs_list_screen",
        "desc": "Songs list screen showing all songs with overflow menu icons",
        "verify": "resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "id": "song1_menu_open",
        "desc": "Context menu open for the first song showing options including 'Add to playing queue'",
        "verify": "text=Add to playing queue"
      },
      {
        "id": "song1_added_to_queue",
        "desc": "First song added to playing queue, songs list visible again",
        "verify": "resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "id": "song2_menu_open",
        "desc": "Context menu open for the second song showing options including 'Add to playing queue'",
        "verify": "text=Add to playing queue"
      },
      {
        "id": "song2_added_to_queue",
        "desc": "Second song added to playing queue, songs list visible again",
        "verify": "resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "id": "song3_menu_open",
        "desc": "Context menu open for the third song showing options including 'Add to playing queue'",
        "verify": "text=Add to playing queue"
      },
      {
        "id": "song3_added_to_queue",
        "desc": "Third song added to playing queue, songs list visible again",
        "verify": "resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "id": "song4_menu_open",
        "desc": "Context menu open for the fourth song showing options including 'Add to playing queue'",
        "verify": "text=Add to playing queue"
      },
      {
        "id": "song4_added_to_queue",
        "desc": "Fourth song added to playing queue, songs list visible again",
        "verify": "resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "id": "song5_menu_open",
        "desc": "Context menu open for the fifth song showing options including 'Add to playing queue'",
        "verify": "text=Add to playing queue"
      },
      {
        "id": "task_complete",
        "desc": "All five songs have been successfully added to the playing queue in Retro Music",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "retro_music_open",
        "to": "songs_list_screen",
        "action": "click resource_id=code.name.monkey.retromusic:id/action_song"
      },
      {
        "from": "songs_list_screen",
        "to": "song1_menu_open",
        "action": "click resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "from": "song1_menu_open",
        "to": "song1_added_to_queue",
        "action": "click text=Add to playing queue"
      },
      {
        "from": "song1_added_to_queue",
        "to": "song2_menu_open",
        "action": "click resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "from": "song2_menu_open",
        "to": "song2_added_to_queue",
        "action": "click text=Add to playing queue"
      },
      {
        "from": "song2_added_to_queue",
        "to": "song3_menu_open",
        "action": "click resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "from": "song3_menu_open",
        "to": "song3_added_to_queue",
        "action": "click text=Add to playing queue"
      },
      {
        "from": "song3_added_to_queue",
        "to": "song4_menu_open",
        "action": "click resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "from": "song4_menu_open",
        "to": "song4_added_to_queue",
        "action": "click text=Add to playing queue"
      },
      {
        "from": "song4_added_to_queue",
        "to": "song5_menu_open",
        "action": "click resource_id=code.name.monkey.retromusic:id/menu"
      },
      {
        "from": "song5_menu_open",
        "to": "task_complete",
        "action": "click text=Add to playing queue"
      }
    ]
  },
  {
    "task": "Take one photo.",
    "app": "com.android.camera2",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "home_screen",
        "desc": "Android home screen or app launcher with Camera app icon visible",
        "verify": "text=Camera"
      },
      {
        "id": "camera_viewfinder",
        "desc": "Camera app viewfinder screen with shutter button ready to capture a photo",
        "verify": "resource_id=camera2:id/shutter_button"
      },
      {
        "id": "photo_captured",
        "desc": "Photo has been captured successfully; camera returns to viewfinder after shutter press",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "home_screen",
        "to": "camera_viewfinder",
        "action": "click text=Camera&&class=TextView"
      },
      {
        "from": "camera_viewfinder",
        "to": "photo_captured",
        "action": "click resource_id=camera2:id/shutter_button"
      }
    ]
  },
  {
    "task": "Take one video.",
    "app": "com.android.camera2",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "camera_app_open",
        "desc": "Camera app main screen with shutter button visible in photo mode",
        "verify": "resource_id=camera2:id/shutter_button"
      },
      {
        "id": "mode_list_open",
        "desc": "Camera mode list panel is open showing available camera modes including video",
        "verify": "content_desc=Switch to Video Camera"
      },
      {
        "id": "video_mode_active",
        "desc": "Camera is in video mode with the shutter/record button visible and ready",
        "verify": "resource_id=camera2:id/shutter_button&&content_desc=Shutter"
      },
      {
        "id": "video_recording_started",
        "desc": "Video recording is in progress with the stop button visible",
        "verify": "resource_id=camera2:id/shutter_button&&content_desc=Shutter"
      },
      {
        "id": "video_recording_complete",
        "desc": "Video recording has been stopped and saved successfully",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "camera_app_open",
        "to": "mode_list_open",
        "action": "click resource_id=camera2:id/accessibility_mode_toggle_button"
      },
      {
        "from": "mode_list_open",
        "to": "video_mode_active",
        "action": "click content_desc=Switch to Video Camera"
      },
      {
        "from": "video_mode_active",
        "to": "video_recording_started",
        "action": "click resource_id=camera2:id/shutter_button"
      },
      {
        "from": "video_recording_started",
        "to": "video_recording_complete",
        "action": "click resource_id=camera2:id/shutter_button"
      }
    ]
  },
  {
    "task": "Open the file task.html in Downloads in the file manager; when prompted open it with Chrome. Then click the button 5 times, remember the numbers displayed, and enter their product in the form.",
    "app": "com.android.chrome",
    "platform": "android",
    "params": [
      "click_count",
      "answer_value"
    ],
    "states": [
      {
        "id": "files_app_open",
        "desc": "Files app is open showing file listing including task.html",
        "verify": "resource_id=android:id/title&&text=task.html"
      },
      {
        "id": "open_with_dialog",
        "desc": "Open With dialog prompting user to choose an app to open task.html",
        "verify": "resource_id=android:id/button_once&&text=Just once"
      },
      {
        "id": "chrome_signin_prompt",
        "desc": "Chrome sign-in / first-run experience prompt asking to sign in or continue without an acco",
        "verify": "resource_id=chrome:id/signin_fre_dismiss_button&&text=Use wi"
      },
      {
        "id": "chrome_signin_prompt_second",
        "desc": "Second Chrome sign-in prompt screen still showing 'Use without an account' button",
        "verify": "resource_id=chrome:id/signin_fre_dismiss_button&&text=Use wi"
      },
      {
        "id": "files_app_reopen",
        "desc": "Files app is visible again showing task.html in the file listing after dismissing Chrome p",
        "verify": "resource_id=android:id/title&&text=task.html"
      },
      {
        "id": "open_with_dialog_second",
        "desc": "Open With dialog appearing again to select Chrome for opening task.html",
        "verify": "resource_id=android:id/button_once&&text=Just once"
      },
      {
        "id": "task_html_loaded",
        "desc": "task.html is loaded in Chrome showing the 'Click Me' button and an answer input field",
        "verify": "resource_id=button&&text=Click Me"
      },
      {
        "id": "button_clicked_once",
        "desc": "Click Me button has been clicked once; page still showing the button",
        "verify": "resource_id=button&&text=Click Me"
      },
      {
        "id": "button_clicked_twice",
        "desc": "Click Me button has been clicked twice; page still showing the button",
        "verify": "resource_id=button&&text=Click Me"
      },
      {
        "id": "button_clicked_three",
        "desc": "Click Me button has been clicked three times; page still showing the button",
        "verify": "resource_id=button&&text=Click Me"
      },
      {
        "id": "button_clicked_four",
        "desc": "Click Me button has been clicked four times; page still showing the button",
        "verify": "resource_id=button&&text=Click Me"
      },
      {
        "id": "button_clicked_five",
        "desc": "Click Me button has been clicked five times; answer input field is now ready for input",
        "verify": "resource_id=answer"
      },
      {
        "id": "answer_entered",
        "desc": "Answer value has been typed into the answer input field; Submit button is visible",
        "verify": "text=Submit"
      },
      {
        "id": "form_submitted",
        "desc": "Form has been submitted successfully; task is complete",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "files_app_open",
        "to": "open_with_dialog",
        "action": "open \"Files\""
      },
      {
        "from": "files_app_open",
        "to": "open_with_dialog",
        "action": "click resource_id=android:id/title&&text=task.html"
      },
      {
        "from": "open_with_dialog",
        "to": "chrome_signin_prompt",
        "action": "click resource_id=android:id/button_once&&text=Just once"
      },
      {
        "from": "chrome_signin_prompt",
        "to": "chrome_signin_prompt_second",
        "action": "click resource_id=chrome:id/signin_fre_dismiss_button&&text=Use wi"
      },
      {
        "from": "chrome_signin_prompt_second",
        "to": "files_app_reopen",
        "action": "click resource_id=chrome:id/signin_fre_dismiss_button&&text=Use wi"
      },
      {
        "from": "files_app_reopen",
        "to": "open_with_dialog_second",
        "action": "click resource_id=android:id/title&&text=task.html"
      },
      {
        "from": "open_with_dialog_second",
        "to": "task_html_loaded",
        "action": "click resource_id=android:id/button_once&&text=Just once"
      },
      {
        "from": "task_html_loaded",
        "to": "button_clicked_once",
        "action": "click resource_id=button&&text=Click Me"
      },
      {
        "from": "button_clicked_once",
        "to": "button_clicked_twice",
        "action": "click resource_id=button&&text=Click Me"
      },
      {
        "from": "button_clicked_twice",
        "to": "button_clicked_three",
        "action": "click resource_id=button&&text=Click Me"
      },
      {
        "from": "button_clicked_three",
        "to": "button_clicked_four",
        "action": "click resource_id=button&&text=Click Me"
      },
      {
        "from": "button_clicked_four",
        "to": "button_clicked_five",
        "action": "click resource_id=button&&text=Click Me"
      },
      {
        "from": "button_clicked_five",
        "to": "answer_entered",
        "action": "type $answer_value"
      },
      {
        "from": "answer_entered",
        "to": "form_submitted",
        "action": "click text=Submit"
      }
    ]
  },
  {
    "task": "Turn brightness to the min value.",
    "app": "com.android.settings",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "settings_main_screen",
        "desc": "Android Settings main screen with scrollable list of setting categories",
        "verify": "resource_id=settings:id/main_content_scrollable_container"
      },
      {
        "id": "settings_scrolled_down",
        "desc": "Android Settings main screen scrolled down to reveal the Display option",
        "verify": "resource_id=android:id/title&&text=Display"
      },
      {
        "id": "display_settings_screen",
        "desc": "Display settings screen showing brightness, wallpaper, font size, and other display option",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "settings_main_screen",
        "to": "settings_scrolled_down",
        "action": "scroll resource_id=settings:id/main_content_scrollable_container"
      },
      {
        "from": "settings_scrolled_down",
        "to": "display_settings_screen",
        "action": "click resource_id=android:id/title&&text=Display"
      }
    ]
  },
  {
    "task": "Turn bluetooth off.",
    "app": "com.android.settings",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "settings_main_screen",
        "desc": "Android Settings main screen showing top-level settings categories",
        "verify": "resource_id=settings:id/search_action_bar||text=Settings"
      },
      {
        "id": "connected_devices_screen",
        "desc": "Connected Devices settings screen showing Bluetooth, NFC, and other connection options",
        "verify": "text=Connected devices"
      },
      {
        "id": "task_complete",
        "desc": "Task complete — Connected Devices settings screen is open and visible",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "settings_main_screen",
        "to": "connected_devices_screen",
        "action": "open \"Settings\""
      },
      {
        "from": "settings_main_screen",
        "to": "connected_devices_screen",
        "action": "click resource_id=android:id/title&&text=Connected devices"
      },
      {
        "from": "connected_devices_screen",
        "to": "task_complete",
        "action": "evaluate_condition"
      }
    ]
  },
  {
    "task": "Turn brightness to the max value.",
    "app": "com.android.settings",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "settings_main_screen",
        "desc": "Android Settings main screen showing top-level settings categories",
        "verify": "resource_id=settings:id/main_content_scrollable_container"
      },
      {
        "id": "settings_scrolled_to_display",
        "desc": "Settings main screen scrolled down to reveal the Display entry with summary text 'Dark the",
        "verify": "resource_id=android:id/summary&&text=Dark theme, font size, "
      },
      {
        "id": "display_settings_screen",
        "desc": "Display settings screen showing options for dark theme, font size, brightness, and related",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "settings_main_screen",
        "to": "settings_main_screen",
        "action": "open \"Settings\""
      },
      {
        "from": "settings_main_screen",
        "to": "settings_scrolled_to_display",
        "action": "scroll"
      },
      {
        "from": "settings_scrolled_to_display",
        "to": "display_settings_screen",
        "action": "click resource_id=android:id/summary&&text=Dark theme, font size,"
      }
    ]
  },
  {
    "task": "Turn bluetooth on.",
    "app": "com.android.settings",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "settings_main_screen",
        "desc": "Android Settings main screen showing top-level settings categories",
        "verify": "text=Settings"
      },
      {
        "id": "connected_devices_screen",
        "desc": "Connected Devices settings screen showing paired and available devices",
        "verify": "text=Connected devices"
      },
      {
        "id": "connected_devices_top",
        "desc": "Connected Devices screen scrolled to the top, showing all connection options",
        "verify": "text=Connected devices"
      },
      {
        "id": "task_complete",
        "desc": "Task complete — Connected Devices screen is open and scrolled to the top",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "settings_main_screen",
        "to": "connected_devices_screen",
        "action": "open \"Settings\""
      },
      {
        "from": "settings_main_screen",
        "to": "connected_devices_screen",
        "action": "click resource_id=android:id/title&&text=Connected devices"
      },
      {
        "from": "connected_devices_screen",
        "to": "connected_devices_top",
        "action": "scroll"
      },
      {
        "from": "connected_devices_top",
        "to": "task_complete",
        "action": "wait"
      }
    ]
  },
  {
    "task": "Delete all but one of any expenses in pro expense that are exact duplicates, ensuring at least one instance of each unique expense remains.",
    "app": "com.arduia.expense",
    "platform": "android",
    "params": [
      "expense_name"
    ],
    "states": [
      {
        "id": "app_home_screen",
        "desc": "Pro Expense app home screen showing the recent expenses list",
        "verify": "resource_id=com.arduia.expense:id/rv_home"
      },
      {
        "id": "home_scrolled_to_expense",
        "desc": "Home screen scrolled down to reveal the target expense entry in the list",
        "verify": "resource_id=com.arduia.expense:id/rv_home&&class=androidx.re"
      },
      {
        "id": "expense_item_selected",
        "desc": "Expense item long-pressed and context action bar with delete button is visible",
        "verify": "resource_id=com.arduia.expense:id/btn_delete&&class=ImageVie"
      },
      {
        "id": "delete_confirmation_dialog",
        "desc": "Delete confirmation dialog shown with a CONFIRM button to finalize deletion",
        "verify": "resource_id=com.arduia.expense:id/btn_confirm&&text=CONFIRM"
      },
      {
        "id": "expense_deleted_home",
        "desc": "Home screen after expense deletion, showing the MORE button to navigate to full logs",
        "verify": "resource_id=com.arduia.expense:id/btn_more_logs&&text=MORE"
      },
      {
        "id": "full_logs_screen",
        "desc": "Full expense logs screen opened after tapping MORE, showing all expense entries",
        "verify": "resource_id=com.arduia.expense:id/rv_home&&class=androidx.re"
      },
      {
        "id": "logs_scrolled_down",
        "desc": "Full logs screen scrolled down to confirm the deleted expense entry is no longer present",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "app_home_screen",
        "to": "home_scrolled_to_expense",
        "action": "scroll resource_id=com.arduia.expense:id/rv_home"
      },
      {
        "from": "home_scrolled_to_expense",
        "to": "expense_item_selected",
        "action": "wait $expense_name"
      },
      {
        "from": "expense_item_selected",
        "to": "delete_confirmation_dialog",
        "action": "click resource_id=com.arduia.expense:id/btn_delete&&class=ImageVie"
      },
      {
        "from": "delete_confirmation_dialog",
        "to": "expense_deleted_home",
        "action": "click resource_id=com.arduia.expense:id/btn_confirm&&text=CONFIRM"
      },
      {
        "from": "expense_deleted_home",
        "to": "full_logs_screen",
        "action": "click resource_id=com.arduia.expense:id/btn_more_logs&&text=MORE"
      },
      {
        "from": "full_logs_screen",
        "to": "logs_scrolled_down",
        "action": "scroll"
      }
    ]
  },
  {
    "task": "Delete the following expenses from pro expense: Utilities, Dining Out, Specialty Foods.",
    "app": "com.arduia.expense",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "home_screen",
        "desc": "Pro Expense home screen showing recent expense list",
        "verify": "resource_id=com.arduia.expense:id/rv_home"
      },
      {
        "id": "home_scrolled",
        "desc": "Home screen scrolled down to reveal the MORE button for full expense log",
        "verify": "resource_id=com.arduia.expense:id/btn_more_logs"
      },
      {
        "id": "expense_log_screen",
        "desc": "Full expense log screen showing all expense entries in a list",
        "verify": "resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "id": "expense_log_scrolled_1",
        "desc": "Expense log scrolled down to reveal the first target expense entry to delete",
        "verify": "resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "id": "delete_icon_tapped_1",
        "desc": "Delete confirmation panel visible after tapping the delete icon on the first target entry",
        "verify": "resource_id=com.arduia.expense:id/btn_delete"
      },
      {
        "id": "confirm_dialog_1",
        "desc": "Confirmation dialog open asking to confirm deletion of the first expense entry",
        "verify": "resource_id=com.arduia.expense:id/btn_confirm"
      },
      {
        "id": "first_deletion_done",
        "desc": "Expense log screen after first entry has been successfully deleted",
        "verify": "resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "id": "expense_log_scrolled_2a",
        "desc": "Expense log scrolled down first time to locate the second target expense entry",
        "verify": "resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "id": "expense_log_scrolled_2b",
        "desc": "Expense log scrolled down second time to reveal the second target expense entry",
        "verify": "resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "id": "delete_icon_tapped_2",
        "desc": "Delete confirmation panel visible after tapping the delete icon on the second target entry",
        "verify": "resource_id=com.arduia.expense:id/btn_delete"
      },
      {
        "id": "confirm_dialog_2",
        "desc": "Confirmation dialog open asking to confirm deletion of the second expense entry",
        "verify": "resource_id=com.arduia.expense:id/btn_confirm"
      },
      {
        "id": "second_deletion_done",
        "desc": "Expense log screen after second entry has been successfully deleted",
        "verify": "resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "id": "expense_log_scrolled_3",
        "desc": "Expense log scrolled down to reveal the third target expense entry to delete",
        "verify": "resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "id": "delete_icon_tapped_3",
        "desc": "Delete confirmation panel visible after tapping the delete icon on the third target entry",
        "verify": "resource_id=com.arduia.expense:id/btn_delete"
      },
      {
        "id": "confirm_dialog_3",
        "desc": "Confirmation dialog open asking to confirm deletion of the third expense entry",
        "verify": "resource_id=com.arduia.expense:id/btn_confirm"
      },
      {
        "id": "task_complete",
        "desc": "All three target expense entries have been successfully deleted from the expense log",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "home_screen",
        "to": "home_scrolled",
        "action": "scroll resource_id=com.arduia.expense:id/rv_home"
      },
      {
        "from": "home_scrolled",
        "to": "expense_log_screen",
        "action": "click resource_id=com.arduia.expense:id/btn_more_logs&&text=MORE"
      },
      {
        "from": "expense_log_screen",
        "to": "expense_log_scrolled_1",
        "action": "scroll resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "from": "expense_log_scrolled_1",
        "to": "delete_icon_tapped_1",
        "action": "click resource_id=com.arduia.expense:id/imv_delete_icon"
      },
      {
        "from": "delete_icon_tapped_1",
        "to": "confirm_dialog_1",
        "action": "click resource_id=com.arduia.expense:id/btn_delete"
      },
      {
        "from": "confirm_dialog_1",
        "to": "first_deletion_done",
        "action": "click resource_id=com.arduia.expense:id/btn_confirm&&text=CONFIRM"
      },
      {
        "from": "first_deletion_done",
        "to": "expense_log_scrolled_2a",
        "action": "scroll resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "from": "expense_log_scrolled_2a",
        "to": "expense_log_scrolled_2b",
        "action": "scroll resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "from": "expense_log_scrolled_2b",
        "to": "delete_icon_tapped_2",
        "action": "click resource_id=com.arduia.expense:id/imv_delete_icon"
      },
      {
        "from": "delete_icon_tapped_2",
        "to": "confirm_dialog_2",
        "action": "click resource_id=com.arduia.expense:id/btn_delete"
      },
      {
        "from": "confirm_dialog_2",
        "to": "second_deletion_done",
        "action": "click resource_id=com.arduia.expense:id/btn_confirm&&text=CONFIRM"
      },
      {
        "from": "second_deletion_done",
        "to": "expense_log_scrolled_3",
        "action": "scroll resource_id=com.arduia.expense:id/rv_expense"
      },
      {
        "from": "expense_log_scrolled_3",
        "to": "delete_icon_tapped_3",
        "action": "click resource_id=com.arduia.expense:id/imv_delete_icon"
      },
      {
        "from": "delete_icon_tapped_3",
        "to": "confirm_dialog_3",
        "action": "click resource_id=com.arduia.expense:id/btn_delete"
      },
      {
        "from": "confirm_dialog_3",
        "to": "task_complete",
        "action": "click resource_id=com.arduia.expense:id/btn_confirm&&text=CONFIRM"
      }
    ]
  },
  {
    "task": "Record an audio clip and save it with name \"briefing_vJDg.m4a\" using Audio Recorder app.",
    "app": "com.dimowner.audiorecorder",
    "platform": "android",
    "params": [
      "new_filename"
    ],
    "states": [
      {
        "id": "rename_dialog_open",
        "desc": "Rename dialog is open with the filename input field visible and pre-filled with the curren",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "id": "text_selected",
        "desc": "All text in the filename input field is selected after long-press and select-all",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "id": "new_name_entered",
        "desc": "New filename has been typed into the input field and the Save button is ready to be tapped",
        "verify": "resource_id=com.dimowner.audiorecorder:id/dialog_positive_bt"
      },
      {
        "id": "rename_complete",
        "desc": "Recording has been successfully renamed and the dialog has been dismissed",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "rename_dialog_open",
        "to": "text_selected",
        "action": "click resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "from": "text_selected",
        "to": "text_selected",
        "action": "click content_desc=Select all"
      },
      {
        "from": "text_selected",
        "to": "new_name_entered",
        "action": "type $new_filename"
      },
      {
        "from": "new_name_entered",
        "to": "rename_complete",
        "action": "click resource_id=com.dimowner.audiorecorder:id/dialog_positive_bt"
      }
    ]
  },
  {
    "task": "Record an audio clip using Audio Recorder app and save it.",
    "app": "com.dimowner.audiorecorder",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "app_launched",
        "desc": "Audio Recorder app launched showing the welcome/get-started screen",
        "verify": "resource_id=com.dimowner.audiorecorder:id/btn_action"
      },
      {
        "id": "settings_screen",
        "desc": "Audio Recorder settings or format selection screen with an Apply button",
        "verify": "resource_id=com.dimowner.audiorecorder:id/btn_apply"
      },
      {
        "id": "recording_ready",
        "desc": "Audio Recorder main screen ready to record with the record button visible",
        "verify": "resource_id=com.dimowner.audiorecorder:id/btn_record"
      },
      {
        "id": "recording_in_progress",
        "desc": "Audio Recorder actively recording audio with the stop button visible",
        "verify": "resource_id=com.dimowner.audiorecorder:id/btn_record_stop"
      },
      {
        "id": "save_dialog",
        "desc": "Save recording confirmation dialog with a Save button",
        "verify": "resource_id=com.dimowner.audiorecorder:id/dialog_positive_bt"
      },
      {
        "id": "recording_saved",
        "desc": "Recording has been saved successfully and the app returns to the main screen",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "app_launched",
        "to": "settings_screen",
        "action": "click resource_id=com.dimowner.audiorecorder:id/btn_action"
      },
      {
        "from": "settings_screen",
        "to": "recording_ready",
        "action": "click resource_id=com.dimowner.audiorecorder:id/btn_apply"
      },
      {
        "from": "recording_ready",
        "to": "recording_in_progress",
        "action": "click resource_id=com.dimowner.audiorecorder:id/btn_record"
      },
      {
        "from": "recording_in_progress",
        "to": "save_dialog",
        "action": "click resource_id=com.dimowner.audiorecorder:id/btn_record_stop"
      },
      {
        "from": "save_dialog",
        "to": "recording_saved",
        "action": "click resource_id=com.dimowner.audiorecorder:id/dialog_positive_bt"
      }
    ]
  },
  {
    "task": "Record an audio clip and save it with name \"webinar_2023_06_18.m4a\" using Audio Recorder app.",
    "app": "com.dimowner.audiorecorder",
    "platform": "android",
    "params": [
      "new_filename"
    ],
    "states": [
      {
        "id": "audio_recorder_rename_dialog_open",
        "desc": "Audio Recorder rename dialog is open with the filename input field visible",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "id": "input_field_focused",
        "desc": "Filename input field is focused and ready for text selection",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name&&class="
      },
      {
        "id": "text_selected",
        "desc": "All text in the filename input field is selected via Select All",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name&&class="
      },
      {
        "id": "text_cleared",
        "desc": "Filename input field has been cleared and is empty, ready for new input",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name&&class="
      },
      {
        "id": "new_filename_entered",
        "desc": "New filename has been typed into the input field and the Save button is visible",
        "verify": "resource_id=com.dimowner.audiorecorder:id/dialog_positive_bt"
      },
      {
        "id": "rename_complete",
        "desc": "Recording has been successfully renamed and the dialog has been dismissed",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "audio_recorder_rename_dialog_open",
        "to": "input_field_focused",
        "action": "click resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "from": "input_field_focused",
        "to": "text_selected",
        "action": "evaluate_condition"
      },
      {
        "from": "text_selected",
        "to": "text_cleared",
        "action": "click resource_id=inputmethod.latin:id/key_pos_del&&content_desc=D"
      },
      {
        "from": "text_cleared",
        "to": "new_filename_entered",
        "action": "type $new_filename"
      },
      {
        "from": "new_filename_entered",
        "to": "rename_complete",
        "action": "click resource_id=com.dimowner.audiorecorder:id/dialog_positive_bt"
      }
    ]
  },
  {
    "task": "Record an audio clip and save it with name \"2023_06_24_training.m4a\" using Audio Recorder app.",
    "app": "com.dimowner.audiorecorder",
    "platform": "android",
    "params": [
      "recording_filename"
    ],
    "states": [
      {
        "id": "app_launched",
        "desc": "Audio Recorder app launched showing the welcome/get-started screen",
        "verify": "resource_id=com.dimowner.audiorecorder:id/btn_action"
      },
      {
        "id": "format_selection_screen",
        "desc": "Audio format selection screen shown after tapping Get Started",
        "verify": "resource_id=com.dimowner.audiorecorder:id/btn_apply"
      },
      {
        "id": "main_recorder_screen",
        "desc": "Main audio recorder screen with the record button ready to start recording",
        "verify": "resource_id=com.dimowner.audiorecorder:id/btn_record"
      },
      {
        "id": "recording_in_progress",
        "desc": "Audio recording is actively in progress with the stop button visible",
        "verify": "resource_id=com.dimowner.audiorecorder:id/btn_record_stop"
      },
      {
        "id": "save_dialog_shown",
        "desc": "Save recording dialog shown with a filename input field pre-populated",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "id": "filename_selected_all",
        "desc": "Filename input field with all existing text selected via long-press and Select All",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "id": "filename_cleared",
        "desc": "Filename input field cleared after cutting the selected text",
        "verify": "resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "id": "filename_entered",
        "desc": "Custom filename typed into the input field and Save button is available",
        "verify": "resource_id=com.dimowner.audiorecorder:id/dialog_positive_bt"
      },
      {
        "id": "recording_saved",
        "desc": "Recording successfully saved with the custom filename and app returned to main screen",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "app_launched",
        "to": "format_selection_screen",
        "action": "click resource_id=com.dimowner.audiorecorder:id/btn_action"
      },
      {
        "from": "format_selection_screen",
        "to": "main_recorder_screen",
        "action": "click resource_id=com.dimowner.audiorecorder:id/btn_apply"
      },
      {
        "from": "main_recorder_screen",
        "to": "recording_in_progress",
        "action": "click resource_id=com.dimowner.audiorecorder:id/btn_record"
      },
      {
        "from": "recording_in_progress",
        "to": "save_dialog_shown",
        "action": "click resource_id=com.dimowner.audiorecorder:id/btn_record_stop"
      },
      {
        "from": "save_dialog_shown",
        "to": "filename_selected_all",
        "action": "click resource_id=com.dimowner.audiorecorder:id/input_name"
      },
      {
        "from": "filename_selected_all",
        "to": "filename_cleared",
        "action": "click content_desc=Cut"
      },
      {
        "from": "filename_cleared",
        "to": "filename_entered",
        "action": "type $recording_filename"
      },
      {
        "from": "filename_entered",
        "to": "recording_saved",
        "action": "click resource_id=com.dimowner.audiorecorder:id/dialog_positive_bt"
      }
    ]
  },
  {
    "task": "Delete the following recipes from Broccoli app: Turkey and Cheese Panini.",
    "app": "com.flauschcode.broccoli",
    "platform": "android",
    "params": [
      "recipe_title"
    ],
    "states": [
      {
        "id": "broccoli_home",
        "desc": "Broccoli app main screen showing recipe cards list",
        "verify": "resource_id=com.flauschcode.broccoli:id/card_text_view_title"
      },
      {
        "id": "recipe_detail",
        "desc": "Recipe detail screen for the selected recipe showing more options menu button",
        "verify": "content_desc=More options"
      },
      {
        "id": "options_menu_open",
        "desc": "Overflow options menu open showing Delete option",
        "verify": "resource_id=com.flauschcode.broccoli:id/title&&text=Delete"
      },
      {
        "id": "delete_confirmation_dialog",
        "desc": "Delete confirmation dialog asking user to confirm recipe deletion",
        "verify": "resource_id=android:id/button1&&text=DELETE"
      },
      {
        "id": "recipe_deleted",
        "desc": "Recipe has been successfully deleted and user is returned to the recipe list",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "broccoli_home",
        "to": "recipe_detail",
        "action": "click resource_id=com.flauschcode.broccoli:id/card_text_view_title"
      },
      {
        "from": "recipe_detail",
        "to": "options_menu_open",
        "action": "click content_desc=More options"
      },
      {
        "from": "options_menu_open",
        "to": "delete_confirmation_dialog",
        "action": "click resource_id=com.flauschcode.broccoli:id/title&&text=Delete"
      },
      {
        "from": "delete_confirmation_dialog",
        "to": "recipe_deleted",
        "action": "click resource_id=android:id/button1&&text=DELETE"
      }
    ]
  },
  {
    "task": "Open the contacts app. Clear any pop-ups that may appear by granting all permissions that are required.",
    "app": "com.google.android.contacts",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "home_screen",
        "desc": "device home screen before opening Contacts app",
        "verify": "resource_id=contacts:id/og_tooltip_scrim_view"
      },
      {
        "id": "contacts_app_with_tooltip",
        "desc": "Contacts app main screen with an onboarding tooltip overlay visible",
        "verify": "resource_id=contacts:id/og_tooltip_scrim_view"
      },
      {
        "id": "contacts_app_ready",
        "desc": "Contacts app main screen after tooltip overlay has been dismissed",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "home_screen",
        "to": "contacts_app_with_tooltip",
        "action": "open \"Contacts\""
      },
      {
        "from": "contacts_app_with_tooltip",
        "to": "contacts_app_ready",
        "action": "click resource_id=contacts:id/og_tooltip_scrim_view"
      }
    ]
  },
  {
    "task": "Go to the new contact screen and enter the following details: First Name: Jack, Last Name: Lee, Phone: 334-226-5457, Phone Label: Home. Do NOT hit save.",
    "app": "com.google.android.contacts",
    "platform": "android",
    "params": [
      "first_name",
      "last_name",
      "phone_number",
      "phone_label"
    ],
    "states": [
      {
        "id": "contacts_main_screen",
        "desc": "Contacts app main screen showing the contact list and the Create Contact floating action b",
        "verify": "resource_id=contacts:id/floating_action_button"
      },
      {
        "id": "create_contact_form",
        "desc": "New contact creation form with editable fields for first name, last name, and phone number",
        "verify": "class=EditText&&hint=First name"
      },
      {
        "id": "first_name_entered",
        "desc": "Contact form with first name filled in, ready to enter last name",
        "verify": "class=EditText&&hint=Last name"
      },
      {
        "id": "last_name_entered",
        "desc": "Contact form with first and last name filled in, ready to enter phone number",
        "verify": "class=EditText&&hint=Phone"
      },
      {
        "id": "phone_number_entered",
        "desc": "Contact form with phone number filled in, showing the phone type label selector (e.g. Home",
        "verify": "resource_id=android:id/text1&&text=Home"
      },
      {
        "id": "phone_label_selected",
        "desc": "Contact form with phone label selected, all required fields completed and ready to save",
        "verify": "class=EditText&&hint=First name"
      },
      {
        "id": "contact_created",
        "desc": "Contact successfully created with the specified name, phone number, and phone label",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "contacts_main_screen",
        "to": "create_contact_form",
        "action": "click resource_id=contacts:id/floating_action_button"
      },
      {
        "from": "create_contact_form",
        "to": "first_name_entered",
        "action": "type $first_name"
      },
      {
        "from": "first_name_entered",
        "to": "last_name_entered",
        "action": "type $last_name"
      },
      {
        "from": "last_name_entered",
        "to": "phone_number_entered",
        "action": "type $phone_number"
      },
      {
        "from": "phone_number_entered",
        "to": "phone_label_selected",
        "action": "click resource_id=android:id/text1&&text=Home"
      },
      {
        "from": "phone_label_selected",
        "to": "contact_created",
        "action": "click resource_id=contacts:id/toolbar_button"
      }
    ]
  },
  {
    "task": "Create a new contact for Emilia Gonzalez. Their number is +14240925675.",
    "app": "com.google.android.contacts",
    "platform": "android",
    "params": [
      "first_name",
      "last_name",
      "phone_number"
    ],
    "states": [
      {
        "id": "permission_dialog",
        "desc": "Permission request dialog asking to allow contacts access",
        "verify": "resource_id=permissioncontroller:id/permission_allow_button"
      },
      {
        "id": "contacts_main_screen",
        "desc": "Google Contacts main screen with floating action button to create a new contact",
        "verify": "resource_id=contacts:id/floating_action_button"
      },
      {
        "id": "new_contact_form_empty",
        "desc": "New contact creation form with empty first name, last name, and phone fields",
        "verify": "hint=First name&&class=EditText"
      },
      {
        "id": "new_contact_first_name_entered",
        "desc": "New contact form with first name (parameter `first_name`) filled in, ready for last name i",
        "verify": "hint=Last name&&class=EditText"
      },
      {
        "id": "new_contact_last_name_entered",
        "desc": "New contact form with first and last name filled in, ready for phone number input",
        "verify": "hint=Phone&&class=EditText"
      },
      {
        "id": "new_contact_phone_entered",
        "desc": "New contact form with phone number (parameter `phone_number`) entered and phone type dropd",
        "verify": "resource_id=android:id/text1&&text=Mobile&&class=CheckedText"
      },
      {
        "id": "new_contact_phone_type_selected",
        "desc": "New contact form fully filled with first name, last name, phone number, and Mobile type se",
        "verify": "resource_id=contacts:id/toolbar_button&&text=Save"
      },
      {
        "id": "contact_saved",
        "desc": "Contact successfully saved — task complete",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "permission_dialog",
        "to": "contacts_main_screen",
        "action": "click resource_id=permissioncontroller:id/permission_allow_button"
      },
      {
        "from": "contacts_main_screen",
        "to": "new_contact_form_empty",
        "action": "click resource_id=contacts:id/floating_action_button"
      },
      {
        "from": "new_contact_form_empty",
        "to": "new_contact_first_name_entered",
        "action": "type $first_name"
      },
      {
        "from": "new_contact_first_name_entered",
        "to": "new_contact_last_name_entered",
        "action": "type $last_name"
      },
      {
        "from": "new_contact_last_name_entered",
        "to": "new_contact_phone_entered",
        "action": "type $phone_number"
      },
      {
        "from": "new_contact_phone_entered",
        "to": "new_contact_phone_type_selected",
        "action": "click resource_id=android:id/text1&&text=Mobile&&class=CheckedText"
      },
      {
        "from": "new_contact_phone_type_selected",
        "to": "contact_saved",
        "action": "click resource_id=contacts:id/toolbar_button&&text=Save"
      }
    ]
  },
  {
    "task": "Run the stopwatch.",
    "app": "com.google.android.deskclock",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "clock_app_open",
        "desc": "Clock app main screen with tab navigation visible",
        "verify": "resource_id=deskclock:id/tab_menu_stopwatch"
      },
      {
        "id": "stopwatch_tab_active",
        "desc": "Stopwatch tab selected showing the Start button ready to begin timing",
        "verify": "resource_id=deskclock:id/fab&&content_desc=Start"
      },
      {
        "id": "stopwatch_running",
        "desc": "Stopwatch is actively running with the Stop button visible, task complete",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "clock_app_open",
        "to": "stopwatch_tab_active",
        "action": "click resource_id=deskclock:id/tab_menu_stopwatch"
      },
      {
        "from": "stopwatch_tab_active",
        "to": "stopwatch_running",
        "action": "click resource_id=deskclock:id/fab&&content_desc=Start"
      }
    ]
  },
  {
    "task": "Pause the stopwatch.",
    "app": "com.google.android.deskclock",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "home_screen",
        "desc": "Android home screen before launching the Clock app",
        "verify": "class=FrameLayout"
      },
      {
        "id": "clock_main_screen",
        "desc": "Clock app main screen showing the bottom tab navigation including the Stopwatch tab",
        "verify": "resource_id=deskclock:id/tab_menu_stopwatch"
      },
      {
        "id": "stopwatch_screen",
        "desc": "Stopwatch tab is active and the stopwatch interface is displayed",
        "verify": "resource_id=deskclock:id/tab_menu_stopwatch"
      },
      {
        "id": "task_complete",
        "desc": "Task complete — the Clock app is open on the Stopwatch tab",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "home_screen",
        "to": "clock_main_screen",
        "action": "open \"Clock\""
      },
      {
        "from": "clock_main_screen",
        "to": "stopwatch_screen",
        "action": "click resource_id=deskclock:id/tab_menu_stopwatch"
      },
      {
        "from": "stopwatch_screen",
        "to": "task_complete",
        "action": "wait"
      }
    ]
  },
  {
    "task": "Create a timer with 14 hours, 14 minutes, and 17 seconds. Do not start the timer.",
    "app": "com.google.android.deskclock",
    "platform": "android",
    "params": [
      "digit_1",
      "digit_2",
      "digit_3",
      "digit_4",
      "digit_5",
      "digit_6"
    ],
    "states": [
      {
        "id": "clock_app_open",
        "desc": "Clock app main screen with tab navigation visible",
        "verify": "resource_id=deskclock:id/tab_menu_timer"
      },
      {
        "id": "timer_tab_active",
        "desc": "Timer tab is active showing the digit keypad for entering timer duration",
        "verify": "resource_id=deskclock:id/timer_setup_digit_1"
      },
      {
        "id": "digit_1_entered",
        "desc": "First digit entered on the timer keypad",
        "verify": "resource_id=deskclock:id/timer_setup_digit_1"
      },
      {
        "id": "digit_2_entered",
        "desc": "Second digit entered on the timer keypad",
        "verify": "resource_id=deskclock:id/timer_setup_digit_4"
      },
      {
        "id": "digit_3_entered",
        "desc": "Third digit entered on the timer keypad",
        "verify": "resource_id=deskclock:id/timer_setup_digit_1"
      },
      {
        "id": "digit_4_entered",
        "desc": "Fourth digit entered on the timer keypad",
        "verify": "resource_id=deskclock:id/timer_setup_digit_4"
      },
      {
        "id": "digit_5_entered",
        "desc": "Fifth digit entered on the timer keypad",
        "verify": "resource_id=deskclock:id/timer_setup_digit_1"
      },
      {
        "id": "timer_duration_set",
        "desc": "All six digits entered, timer duration fully specified (e.g., 1h 41m 17s)",
        "verify": "resource_id=deskclock:id/timer_setup_digit_7"
      },
      {
        "id": "timer_configured",
        "desc": "Timer duration has been fully entered and is ready to start",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "clock_app_open",
        "to": "timer_tab_active",
        "action": "click resource_id=deskclock:id/tab_menu_timer"
      },
      {
        "from": "timer_tab_active",
        "to": "digit_1_entered",
        "action": "click resource_id=deskclock:id/timer_setup_digit_1"
      },
      {
        "from": "digit_1_entered",
        "to": "digit_2_entered",
        "action": "click resource_id=deskclock:id/timer_setup_digit_4"
      },
      {
        "from": "digit_2_entered",
        "to": "digit_3_entered",
        "action": "click resource_id=deskclock:id/timer_setup_digit_1"
      },
      {
        "from": "digit_3_entered",
        "to": "digit_4_entered",
        "action": "click resource_id=deskclock:id/timer_setup_digit_4"
      },
      {
        "from": "digit_4_entered",
        "to": "digit_5_entered",
        "action": "click resource_id=deskclock:id/timer_setup_digit_1"
      },
      {
        "from": "digit_5_entered",
        "to": "timer_duration_set",
        "action": "click resource_id=deskclock:id/timer_setup_digit_7"
      },
      {
        "from": "timer_duration_set",
        "to": "timer_configured",
        "action": "wait"
      }
    ]
  },
  {
    "task": "Delete the file pretty_apple_copy.pdf from the Android filesystem located in the Documents folder within the sdk_gphone_x86_64 storage area.",
    "app": "com.google.android.documentsui",
    "platform": "android",
    "params": [
      "filename"
    ],
    "states": [
      {
        "id": "files_app_main",
        "desc": "Files app main screen with navigation drawer toggle visible",
        "verify": "content_desc=Show roots"
      },
      {
        "id": "roots_drawer_open",
        "desc": "Navigation drawer open showing storage roots including device storage",
        "verify": "text=sdk_gphone64_x86_64"
      },
      {
        "id": "device_storage_root",
        "desc": "Device storage root directory listing showing folders including Documents",
        "verify": "resource_id=android:id/title&&text=Documents"
      },
      {
        "id": "documents_folder",
        "desc": "Documents folder open showing list of files including the target PDF",
        "verify": "resource_id=android:id/title&&text=pretty_apple_copy.pdf"
      },
      {
        "id": "file_selected",
        "desc": "Target file selected via long press with contextual action bar showing Delete option",
        "verify": "resource_id=documentsui:id/action_menu_delete"
      },
      {
        "id": "delete_confirmation_dialog",
        "desc": "Delete confirmation dialog asking user to confirm file deletion with OK button",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "file_deleted",
        "desc": "File successfully deleted and removed from the Documents folder",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "files_app_main",
        "to": "roots_drawer_open",
        "action": "click content_desc=Show roots"
      },
      {
        "from": "roots_drawer_open",
        "to": "device_storage_root",
        "action": "click resource_id=android:id/title&&text=sdk_gphone64_x86_64"
      },
      {
        "from": "device_storage_root",
        "to": "documents_folder",
        "action": "click resource_id=android:id/title&&text=Documents"
      },
      {
        "from": "documents_folder",
        "to": "file_selected",
        "action": "wait $filename"
      },
      {
        "from": "file_selected",
        "to": "delete_confirmation_dialog",
        "action": "click resource_id=documentsui:id/action_menu_delete"
      },
      {
        "from": "delete_confirmation_dialog",
        "to": "file_deleted",
        "action": "click resource_id=android:id/button1&&text=OK"
      }
    ]
  },
  {
    "task": "Delete the file 2023_09_01_strong_dog.mp3 from the Android filesystem located in the Podcasts folder within the sdk_gphone_x86_64 storage area.",
    "app": "com.google.android.documentsui",
    "platform": "android",
    "params": [
      "folder_name",
      "file_name"
    ],
    "states": [
      {
        "id": "files_app_open",
        "desc": "Files app main screen with navigation drawer toggle visible",
        "verify": "content_desc=Show roots"
      },
      {
        "id": "roots_drawer_open",
        "desc": "Navigation drawer open showing storage roots including device internal storage",
        "verify": "text=sdk_gphone64_x86_64"
      },
      {
        "id": "device_storage_root",
        "desc": "Device internal storage root directory listing showing folders including Podcasts",
        "verify": "resource_id=android:id/title&&text=Podcasts"
      },
      {
        "id": "podcasts_folder_open",
        "desc": "Podcasts folder open showing list of podcast audio files",
        "verify": "resource_id=android:id/title&&text=2023_09_01_strong_dog.mp3"
      },
      {
        "id": "file_selected",
        "desc": "File long-pressed and selected with contextual action bar showing Delete option",
        "verify": "resource_id=documentsui:id/action_menu_delete"
      },
      {
        "id": "delete_confirmation_dialog",
        "desc": "Delete confirmation dialog asking user to confirm file deletion with OK button",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "file_deleted",
        "desc": "File successfully deleted and removed from the Podcasts folder",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "files_app_open",
        "to": "roots_drawer_open",
        "action": "open \"Files\""
      },
      {
        "from": "files_app_open",
        "to": "roots_drawer_open",
        "action": "click content_desc=Show roots"
      },
      {
        "from": "roots_drawer_open",
        "to": "device_storage_root",
        "action": "click resource_id=android:id/title&&text=sdk_gphone64_x86_64"
      },
      {
        "from": "device_storage_root",
        "to": "podcasts_folder_open",
        "action": "click resource_id=android:id/title&&text=Podcasts"
      },
      {
        "from": "podcasts_folder_open",
        "to": "file_selected",
        "action": "click resource_id=android:id/title&&parameter_name=file_name"
      },
      {
        "from": "file_selected",
        "to": "delete_confirmation_dialog",
        "action": "click resource_id=documentsui:id/action_menu_delete"
      },
      {
        "from": "delete_confirmation_dialog",
        "to": "file_deleted",
        "action": "click resource_id=android:id/button1&&text=OK"
      }
    ]
  },
  {
    "task": "Move the file jazzy_ring.mp3 from Documents within the sdk_gphone_x86_64 storage area to the Ringtones within the same sdk_gphone_x86_64 storage area in the Android filesystem.",
    "app": "com.google.android.documentsui",
    "platform": "android",
    "params": [
      "filename"
    ],
    "states": [
      {
        "id": "files_app_open",
        "desc": "Files app is open showing the main document browser with the Show roots button visible",
        "verify": "content_desc=Show roots"
      },
      {
        "id": "roots_drawer_open",
        "desc": "Roots/sidebar drawer is open showing storage locations including the device internal stora",
        "verify": "resource_id=android:id/title&&text=sdk_gphone64_x86_64"
      },
      {
        "id": "device_storage_open",
        "desc": "Device internal storage root is open showing top-level folders including Documents",
        "verify": "resource_id=android:id/title&&text=Documents"
      },
      {
        "id": "documents_folder_open",
        "desc": "Documents folder is open showing its file listing in a scrollable list",
        "verify": "resource_id=documentsui:id/dir_list"
      },
      {
        "id": "documents_folder_scrolled",
        "desc": "Documents folder list has been scrolled down and the target file is now visible",
        "verify": "resource_id=android:id/title&&text=jazzy_ring.mp3"
      },
      {
        "id": "file_selected",
        "desc": "Target file is long-pressed and selected, showing the action bar with More options menu",
        "verify": "content_desc=More options"
      },
      {
        "id": "more_options_menu_open",
        "desc": "More options overflow menu is open showing file actions including Move to…",
        "verify": "resource_id=documentsui:id/title&&text=Move to…"
      },
      {
        "id": "move_destination_picker_open",
        "desc": "Move destination picker is open, showing the file browser to select a destination folder",
        "verify": "content_desc=Show roots"
      },
      {
        "id": "move_roots_drawer_open",
        "desc": "Roots/sidebar drawer is open in the move destination picker showing storage locations",
        "verify": "resource_id=android:id/title&&text=sdk_gphone64_x86_64"
      },
      {
        "id": "move_device_storage_open",
        "desc": "Device internal storage root is open in the move picker showing folders including Ringtone",
        "verify": "resource_id=android:id/title&&text=Ringtones"
      },
      {
        "id": "ringtones_folder_selected",
        "desc": "Ringtones folder is selected as the move destination and the MOVE confirmation button is v",
        "verify": "resource_id=android:id/button1&&text=MOVE"
      },
      {
        "id": "move_complete",
        "desc": "File has been successfully moved to the Ringtones folder and the task is complete",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "files_app_open",
        "to": "roots_drawer_open",
        "action": "click content_desc=Show roots"
      },
      {
        "from": "roots_drawer_open",
        "to": "device_storage_open",
        "action": "click resource_id=android:id/title&&text=sdk_gphone64_x86_64"
      },
      {
        "from": "device_storage_open",
        "to": "documents_folder_open",
        "action": "click resource_id=android:id/title&&text=Documents"
      },
      {
        "from": "documents_folder_open",
        "to": "documents_folder_scrolled",
        "action": "scroll resource_id=documentsui:id/dir_list"
      },
      {
        "from": "documents_folder_scrolled",
        "to": "file_selected",
        "action": "wait resource_id=android:id/title&&text=jazzy_ring.mp3"
      },
      {
        "from": "file_selected",
        "to": "more_options_menu_open",
        "action": "click content_desc=More options"
      },
      {
        "from": "more_options_menu_open",
        "to": "move_destination_picker_open",
        "action": "click resource_id=documentsui:id/title&&text=Move to…"
      },
      {
        "from": "move_destination_picker_open",
        "to": "move_roots_drawer_open",
        "action": "click content_desc=Show roots"
      },
      {
        "from": "move_roots_drawer_open",
        "to": "move_device_storage_open",
        "action": "click resource_id=android:id/title&&text=sdk_gphone64_x86_64"
      },
      {
        "from": "move_device_storage_open",
        "to": "ringtones_folder_selected",
        "action": "click resource_id=android:id/title&&text=Ringtones"
      },
      {
        "from": "ringtones_folder_selected",
        "to": "move_complete",
        "action": "click resource_id=android:id/button1&&text=MOVE"
      }
    ]
  },
  {
    "task": "In Simple Calendar Pro, delete the calendar event on 2023-10-17 at 21h with the title 'Workshop on Annual Report'",
    "app": "com.simplemobiletools.calendar.pro",
    "platform": "android",
    "params": [
      "event_title",
      "navigation_steps"
    ],
    "states": [
      {
        "id": "calendar_main_screen",
        "desc": "Simple Calendar Pro main screen showing the monthly calendar view",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/month_view"
      },
      {
        "id": "day_view_opened",
        "desc": "Day or event list view opened after tapping a date on the monthly calendar",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "navigated_month_1",
        "desc": "Calendar navigated forward by one month using the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "navigated_month_2",
        "desc": "Calendar navigated forward by two months using the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "navigated_month_3",
        "desc": "Calendar navigated forward by three months using the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "navigated_month_4",
        "desc": "Calendar navigated forward by four months using the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "navigated_month_5",
        "desc": "Calendar navigated forward by five months using the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "navigated_month_6",
        "desc": "Calendar navigated forward by six months using the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "event_selected",
        "desc": "Event selected via long-press, contextual action bar (CAB) visible with Delete button",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/cab_delete"
      },
      {
        "id": "delete_confirmation_dialog",
        "desc": "Confirmation dialog asking whether to delete the selected event, with Yes and No buttons",
        "verify": "resource_id=android:id/button1&&text=Yes"
      },
      {
        "id": "event_deleted",
        "desc": "Event successfully deleted; calendar view is displayed without the deleted event",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "calendar_main_screen",
        "to": "day_view_opened",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/month_view"
      },
      {
        "from": "day_view_opened",
        "to": "navigated_month_1",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "navigated_month_1",
        "to": "navigated_month_2",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "navigated_month_2",
        "to": "navigated_month_3",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "navigated_month_3",
        "to": "navigated_month_4",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "navigated_month_4",
        "to": "navigated_month_5",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "navigated_month_5",
        "to": "navigated_month_6",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "navigated_month_6",
        "to": "event_selected",
        "action": "wait $event_title"
      },
      {
        "from": "event_selected",
        "to": "delete_confirmation_dialog",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/cab_delete"
      },
      {
        "from": "delete_confirmation_dialog",
        "to": "event_deleted",
        "action": "click resource_id=android:id/button1&&text=Yes"
      }
    ]
  },
  {
    "task": "In Simple Calendar Pro, delete all events scheduled for this Thursday.",
    "app": "com.simplemobiletools.calendar.pro",
    "platform": "android",
    "params": [
      "event_title_1",
      "event_title_2",
      "days_forward"
    ],
    "states": [
      {
        "id": "calendar_main_view",
        "desc": "Calendar app main screen with the change-view button visible in the toolbar",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/change_vie"
      },
      {
        "id": "change_view_dialog",
        "desc": "Change view dialog showing view options including Daily view radio button",
        "verify": "text=Daily view"
      },
      {
        "id": "daily_view_active",
        "desc": "Calendar in daily view with navigation arrows visible to move between days",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "daily_view_day2",
        "desc": "Daily view advanced one day forward after first tap of the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "daily_view_day3",
        "desc": "Daily view advanced two days forward after second tap of the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "daily_view_day4",
        "desc": "Daily view advanced three days forward after third tap of the right arrow",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "id": "daily_view_target_day",
        "desc": "Daily view on the target day showing events including 'Call with Marketing' and 'Meeting w",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_item"
      },
      {
        "id": "multiselect_mode_first_selected",
        "desc": "Contextual action bar (CAB) active after long-pressing 'Call with Marketing', with the fir",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/cab_delete"
      },
      {
        "id": "multiselect_mode_both_selected",
        "desc": "Both 'Call with Marketing' and 'Meeting with HR' selected in multi-select mode, delete but",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/cab_delete"
      },
      {
        "id": "delete_confirmation_dialog",
        "desc": "Delete confirmation dialog asking the user to confirm deletion of the selected events",
        "verify": "resource_id=android:id/button1&&text=Yes"
      },
      {
        "id": "events_deleted_terminal",
        "desc": "Task complete — both selected events have been deleted and the calendar daily view is show",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "calendar_main_view",
        "to": "change_view_dialog",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/change_vie"
      },
      {
        "from": "change_view_dialog",
        "to": "daily_view_active",
        "action": "click text=Daily view"
      },
      {
        "from": "daily_view_active",
        "to": "daily_view_day2",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "daily_view_day2",
        "to": "daily_view_day3",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "daily_view_day3",
        "to": "daily_view_day4",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "daily_view_day4",
        "to": "daily_view_target_day",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/top_right_"
      },
      {
        "from": "daily_view_target_day",
        "to": "multiselect_mode_first_selected",
        "action": "wait resource_id=com.simplemobiletools.calendar.pro:id/event_item"
      },
      {
        "from": "multiselect_mode_first_selected",
        "to": "multiselect_mode_both_selected",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/event_item"
      },
      {
        "from": "multiselect_mode_both_selected",
        "to": "delete_confirmation_dialog",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/cab_delete"
      },
      {
        "from": "delete_confirmation_dialog",
        "to": "events_deleted_terminal",
        "action": "click resource_id=android:id/button1&&text=Yes"
      }
    ]
  },
  {
    "task": "In Simple Calendar Pro, create a calendar event for tomorrow at 10h with the title 'Call with Alice' and the description 'We will celebrate contract details. Looking forward to productive discussions.'. The event should last for 45 mins.",
    "app": "com.simplemobiletools.calendar.pro",
    "platform": "android",
    "params": [
      "event_title",
      "event_description",
      "event_day",
      "event_day_desc",
      "event_start_hour",
      "event_end_minute"
    ],
    "states": [
      {
        "id": "calendar_main_screen",
        "desc": "Simple Calendar Pro main screen with the New Event FAB button visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/calendar_f"
      },
      {
        "id": "event_type_selection",
        "desc": "Event type selection menu showing Event and Task options",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/fab_event_"
      },
      {
        "id": "new_event_form",
        "desc": "New event creation form with title and description fields",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_titl"
      },
      {
        "id": "event_title_entered",
        "desc": "New event form after entering the event title, description field ready for input",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_desc"
      },
      {
        "id": "event_description_entered",
        "desc": "New event form after entering title and description, start date field visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_star"
      },
      {
        "id": "date_picker_dialog",
        "desc": "Date picker dialog open for selecting the event date",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "date_day_selected",
        "desc": "Date picker with the target day selected, ready to confirm",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "event_form_date_set",
        "desc": "New event form with date confirmed, start time field visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_star"
      },
      {
        "id": "start_time_picker",
        "desc": "Time picker dialog open for selecting the event start time",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "id": "start_time_hour_selected",
        "desc": "Start time picker with hour selected, ready to confirm minutes",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "id": "start_time_confirmed",
        "desc": "New event form with start time confirmed, end time field visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_end_"
      },
      {
        "id": "end_time_picker",
        "desc": "Time picker dialog open for selecting the event end time",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/material_m"
      },
      {
        "id": "end_time_minute_mode",
        "desc": "End time picker in minute selection mode after tapping the minutes field",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "id": "end_time_confirmed",
        "desc": "New event form with all fields filled and end time confirmed, ready to save",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/save"
      },
      {
        "id": "duplicate_event_dialog",
        "desc": "Confirmation dialog (e.g. duplicate event or save confirmation) after tapping Save",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "event_saved",
        "desc": "Event successfully saved and returned to the calendar main screen",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "calendar_main_screen",
        "to": "event_type_selection",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/calendar_f"
      },
      {
        "from": "event_type_selection",
        "to": "new_event_form",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/fab_event_"
      },
      {
        "from": "new_event_form",
        "to": "event_title_entered",
        "action": "type $event_title"
      },
      {
        "from": "event_title_entered",
        "to": "event_description_entered",
        "action": "type $event_description"
      },
      {
        "from": "event_description_entered",
        "to": "date_picker_dialog",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/event_star"
      },
      {
        "from": "date_picker_dialog",
        "to": "date_day_selected",
        "action": "click $event_day_desc"
      },
      {
        "from": "date_day_selected",
        "to": "event_form_date_set",
        "action": "click resource_id=android:id/button1&&text=OK"
      },
      {
        "from": "event_form_date_set",
        "to": "start_time_picker",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/event_star"
      },
      {
        "from": "start_time_picker",
        "to": "start_time_hour_selected",
        "action": "click $event_start_hour"
      },
      {
        "from": "start_time_hour_selected",
        "to": "start_time_confirmed",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "from": "start_time_confirmed",
        "to": "end_time_picker",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/event_end_"
      },
      {
        "from": "end_time_picker",
        "to": "end_time_minute_mode",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/material_m"
      },
      {
        "from": "end_time_minute_mode",
        "to": "end_time_confirmed",
        "action": "click $event_end_minute"
      },
      {
        "from": "end_time_confirmed",
        "to": "duplicate_event_dialog",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/save"
      },
      {
        "from": "duplicate_event_dialog",
        "to": "event_saved",
        "action": "click resource_id=android:id/button1&&text=OK"
      }
    ]
  },
  {
    "task": "In Simple Calendar Pro, create a recurring calendar event titled 'Catch up on Annual Report' starting on 2023-10-23 at 2h. The event recurs daily, forever, and lasts for 15 minutes each occurrence. The event description should be 'We will organize upcoming project milestones.'.",
    "app": "com.simplemobiletools.calendar.pro",
    "platform": "android",
    "params": [
      "event_title",
      "event_description",
      "event_start_day",
      "event_start_hour",
      "event_start_minute",
      "event_end_minute",
      "repetition_type"
    ],
    "states": [
      {
        "id": "calendar_main",
        "desc": "Simple Calendar Pro main screen with the New Event FAB visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/calendar_f"
      },
      {
        "id": "event_type_menu",
        "desc": "Event type selection menu showing Event and Task options",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/fab_event_"
      },
      {
        "id": "new_event_form",
        "desc": "New event creation form with title and description fields",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_titl"
      },
      {
        "id": "event_form_title_entered",
        "desc": "New event form after the event title has been entered, description field ready",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_desc"
      },
      {
        "id": "event_form_description_entered",
        "desc": "New event form after title and description entered, start date field visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_star"
      },
      {
        "id": "date_picker_dialog",
        "desc": "Date picker dialog for selecting the event start date",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "date_day_selected",
        "desc": "Date picker dialog with the target day selected, ready to confirm",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "event_form_date_set",
        "desc": "New event form after start date is set, start time field visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_star"
      },
      {
        "id": "start_time_picker_hour",
        "desc": "Start time picker dialog showing hour selection",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "id": "start_time_picker_minute",
        "desc": "Start time picker dialog after hour selected, showing minute selection",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "id": "event_form_start_time_set",
        "desc": "New event form after start time is set, end time field visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_end_"
      },
      {
        "id": "end_time_picker_minute_mode",
        "desc": "End time picker dialog showing minute selection mode",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/material_m"
      },
      {
        "id": "end_time_picker_minute_selected",
        "desc": "End time picker dialog with target minute selected, ready to confirm",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "id": "event_form_times_set",
        "desc": "New event form with start and end times set, repetition field visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/event_repe"
      },
      {
        "id": "repetition_dialog",
        "desc": "Repetition selection dialog showing repetition options including Daily",
        "verify": "text=Daily&&class=RadioButton"
      },
      {
        "id": "event_form_repetition_set",
        "desc": "New event form fully filled out with repetition set, Save button visible",
        "verify": "resource_id=com.simplemobiletools.calendar.pro:id/save"
      },
      {
        "id": "repetition_confirm_dialog",
        "desc": "Confirmation dialog asking how to apply the repetition rule when saving",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "event_saved_terminal",
        "desc": "Event successfully saved and app returned to the calendar main screen",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "calendar_main",
        "to": "event_type_menu",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/calendar_f"
      },
      {
        "from": "event_type_menu",
        "to": "new_event_form",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/fab_event_"
      },
      {
        "from": "new_event_form",
        "to": "event_form_title_entered",
        "action": "type $event_title"
      },
      {
        "from": "event_form_title_entered",
        "to": "event_form_description_entered",
        "action": "type $event_description"
      },
      {
        "from": "event_form_description_entered",
        "to": "date_picker_dialog",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/event_star"
      },
      {
        "from": "date_picker_dialog",
        "to": "date_day_selected",
        "action": "click content_desc=23 October 2023"
      },
      {
        "from": "date_day_selected",
        "to": "event_form_date_set",
        "action": "click resource_id=android:id/button1&&text=OK"
      },
      {
        "from": "event_form_date_set",
        "to": "start_time_picker_hour",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/event_star"
      },
      {
        "from": "start_time_picker_hour",
        "to": "start_time_picker_minute",
        "action": "click content_desc=2 hours"
      },
      {
        "from": "start_time_picker_minute",
        "to": "event_form_start_time_set",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "from": "event_form_start_time_set",
        "to": "end_time_picker_minute_mode",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/event_end_"
      },
      {
        "from": "end_time_picker_minute_mode",
        "to": "end_time_picker_minute_selected",
        "action": "click content_desc=15 minutes"
      },
      {
        "from": "end_time_picker_minute_selected",
        "to": "event_form_times_set",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/material_t"
      },
      {
        "from": "event_form_times_set",
        "to": "repetition_dialog",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/event_repe"
      },
      {
        "from": "repetition_dialog",
        "to": "event_form_repetition_set",
        "action": "click text=Daily&&class=RadioButton"
      },
      {
        "from": "event_form_repetition_set",
        "to": "repetition_confirm_dialog",
        "action": "click resource_id=com.simplemobiletools.calendar.pro:id/save"
      },
      {
        "from": "repetition_confirm_dialog",
        "to": "event_saved_terminal",
        "action": "click resource_id=android:id/button1&&text=OK"
      }
    ]
  },
  {
    "task": "Create a new drawing in Simple Draw Pro. Name it lorem_tough_dog_final.jpg. Save it in the Pictures folder within the sdk_gphone_x86_64 storage area.",
    "app": "com.simplemobiletools.draw.pro",
    "platform": "android",
    "params": [
      "filename"
    ],
    "states": [
      {
        "id": "draw_canvas",
        "desc": "Simple Draw Pro main canvas screen with toolbar visible",
        "verify": "resource_id=com.simplemobiletools.draw.pro:id/menu_save"
      },
      {
        "id": "save_dialog_open",
        "desc": "Save image dialog open with filename input field visible",
        "verify": "resource_id=com.simplemobiletools.draw.pro:id/save_image_fil"
      },
      {
        "id": "filename_cleared",
        "desc": "Save image dialog with filename field cleared and ready for new input",
        "verify": "resource_id=com.simplemobiletools.draw.pro:id/save_image_fil"
      },
      {
        "id": "filename_entered",
        "desc": "Save image dialog with new filename typed and format options visible",
        "verify": "resource_id=com.simplemobiletools.draw.pro:id/save_image_rad"
      },
      {
        "id": "jpg_selected",
        "desc": "Save image dialog with JPG format selected and OK button ready",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "file_picker_open",
        "desc": "Android file picker / directory chooser dialog open",
        "verify": "content_desc=Show roots"
      },
      {
        "id": "roots_shown",
        "desc": "File picker roots panel showing available storage locations including device storage",
        "verify": "resource_id=android:id/title&&text=sdk_gphone64_x86_64"
      },
      {
        "id": "device_storage_open",
        "desc": "Device internal storage root directory listing with Pictures folder visible",
        "verify": "resource_id=android:id/title&&text=Pictures"
      },
      {
        "id": "pictures_folder_open",
        "desc": "Pictures folder selected in file picker with SAVE button ready",
        "verify": "resource_id=android:id/button1&&text=SAVE"
      },
      {
        "id": "image_saved",
        "desc": "Image successfully saved to Pictures folder; app returns to canvas screen",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "draw_canvas",
        "to": "save_dialog_open",
        "action": "click resource_id=com.simplemobiletools.draw.pro:id/menu_save"
      },
      {
        "from": "save_dialog_open",
        "to": "filename_cleared",
        "action": "type resource_id=com.simplemobiletools.draw.pro:id/save_image_fil"
      },
      {
        "from": "filename_cleared",
        "to": "filename_entered",
        "action": "type $filename"
      },
      {
        "from": "filename_entered",
        "to": "jpg_selected",
        "action": "click resource_id=com.simplemobiletools.draw.pro:id/save_image_rad"
      },
      {
        "from": "jpg_selected",
        "to": "file_picker_open",
        "action": "click resource_id=android:id/button1&&text=OK"
      },
      {
        "from": "file_picker_open",
        "to": "roots_shown",
        "action": "click content_desc=Show roots"
      },
      {
        "from": "roots_shown",
        "to": "device_storage_open",
        "action": "click resource_id=android:id/title&&text=sdk_gphone64_x86_64"
      },
      {
        "from": "device_storage_open",
        "to": "pictures_folder_open",
        "action": "click resource_id=android:id/title&&text=Pictures"
      },
      {
        "from": "pictures_folder_open",
        "to": "image_saved",
        "action": "click resource_id=android:id/button1&&text=SAVE"
      }
    ]
  },
  {
    "task": "In Simple Gallery Pro, copy receipt_copy_proud_monkey.jpg in DCIM and save a copy with the same name in Download",
    "app": "com.simplemobiletools.gallery.pro",
    "platform": "android",
    "params": [
      "source_folder",
      "destination_folder"
    ],
    "states": [
      {
        "id": "gallery_home",
        "desc": "Simple Gallery Pro main screen showing folder list",
        "verify": "resource_id=com.simplemobiletools.gallery.pro:id/dir_name"
      },
      {
        "id": "dcim_folder_open",
        "desc": "DCIM folder open showing media items grid",
        "verify": "resource_id=com.simplemobiletools.gallery.pro:id/media_item_"
      },
      {
        "id": "item_selected",
        "desc": "Media item long-pressed and selected, action bar visible with More options button",
        "verify": "content_desc=More options"
      },
      {
        "id": "overflow_menu_open",
        "desc": "Overflow context menu open showing options including Copy to",
        "verify": "resource_id=com.simplemobiletools.gallery.pro:id/title&&text"
      },
      {
        "id": "copy_destination_dialog",
        "desc": "Copy destination dialog showing folder options including Other folder button",
        "verify": "resource_id=android:id/button3&&text=Other folder"
      },
      {
        "id": "folder_picker_open",
        "desc": "Folder picker screen open at Internal storage root with breadcrumb navigation",
        "verify": "resource_id=com.simplemobiletools.gallery.pro:id/breadcrumb_"
      },
      {
        "id": "download_folder_selected",
        "desc": "Download folder selected in folder picker, OK button visible to confirm copy destination",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "copy_complete",
        "desc": "Copy operation completed successfully, media item copied to Download folder",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "gallery_home",
        "to": "dcim_folder_open",
        "action": "click resource_id=com.simplemobiletools.gallery.pro:id/dir_name&&t"
      },
      {
        "from": "dcim_folder_open",
        "to": "item_selected",
        "action": "wait resource_id=com.simplemobiletools.gallery.pro:id/media_item_"
      },
      {
        "from": "item_selected",
        "to": "overflow_menu_open",
        "action": "click content_desc=More options"
      },
      {
        "from": "overflow_menu_open",
        "to": "copy_destination_dialog",
        "action": "click resource_id=com.simplemobiletools.gallery.pro:id/title&&text"
      },
      {
        "from": "copy_destination_dialog",
        "to": "folder_picker_open",
        "action": "click resource_id=android:id/button3&&text=Other folder"
      },
      {
        "from": "folder_picker_open",
        "to": "folder_picker_open",
        "action": "click resource_id=com.simplemobiletools.gallery.pro:id/breadcrumb_"
      },
      {
        "from": "folder_picker_open",
        "to": "download_folder_selected",
        "action": "click resource_id=com.simplemobiletools.gallery.pro:id/list_item_n"
      },
      {
        "from": "download_folder_selected",
        "to": "copy_complete",
        "action": "click resource_id=android:id/button1&&text=OK"
      }
    ]
  },
  {
    "task": "Delete the note in Markor named final_polite_fish.",
    "app": "net.gsantner.markor",
    "platform": "android",
    "params": [
      "file_name"
    ],
    "states": [
      {
        "id": "markor_home",
        "desc": "Markor main file browser screen showing list of files and folders",
        "verify": "resource_id=net.gsantner.markor:id/opoc_filesystem_item__roo"
      },
      {
        "id": "file_selected",
        "desc": "File is selected via long-press, contextual action bar visible with delete option",
        "verify": "resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "id": "delete_confirmation_dialog",
        "desc": "Delete confirmation dialog asking user to confirm file deletion",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "file_deleted",
        "desc": "File has been successfully deleted and Markor returns to the file browser",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "markor_home",
        "to": "markor_home",
        "action": "open \"Markor\""
      },
      {
        "from": "markor_home",
        "to": "file_selected",
        "action": "click $file_name"
      },
      {
        "from": "file_selected",
        "to": "delete_confirmation_dialog",
        "action": "click resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "from": "delete_confirmation_dialog",
        "to": "file_deleted",
        "action": "click resource_id=android:id/button1&&text=OK"
      }
    ]
  },
  {
    "task": "Create a new note in Markor named safe_ocean_T3go.md with the following text: Beauty is in the eye of the beholder.",
    "app": "net.gsantner.markor",
    "platform": "android",
    "params": [
      "filename",
      "note_content"
    ],
    "states": [
      {
        "id": "markor_new_file_dialog_open",
        "desc": "Markor new file dialog is open with file type selector and filename input field",
        "verify": "resource_id=net.gsantner.markor:id/new_file_dialog__name"
      },
      {
        "id": "file_type_selected_name_entered",
        "desc": "Markdown file type is selected and the filename has been entered in the new file dialog",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "editor_open",
        "desc": "Markor markdown editor is open and ready for text input",
        "verify": "resource_id=net.gsantner.markor:id/document__fragment__edit_"
      },
      {
        "id": "content_entered",
        "desc": "Note content has been typed into the editor and the save button is visible in the toolbar",
        "verify": "resource_id=net.gsantner.markor:id/action_save"
      },
      {
        "id": "note_saved",
        "desc": "Note has been saved successfully; editor remains open with the saved content",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "markor_new_file_dialog_open",
        "to": "file_type_selected_name_entered",
        "action": "click resource_id=android:id/text1&&text=Markdown"
      },
      {
        "from": "file_type_selected_name_entered",
        "to": "file_type_selected_name_entered",
        "action": "type $filename"
      },
      {
        "from": "file_type_selected_name_entered",
        "to": "editor_open",
        "action": "click resource_id=android:id/button1&&text=OK"
      },
      {
        "from": "editor_open",
        "to": "content_entered",
        "action": "type $note_content"
      },
      {
        "from": "content_entered",
        "to": "note_saved",
        "action": "click resource_id=net.gsantner.markor:id/action_save"
      }
    ]
  },
  {
    "task": "Create a new note in Markor named brave_violin_2c5o.md with the following text: The library book is due back on the 15th.",
    "app": "net.gsantner.markor",
    "platform": "android",
    "params": [
      "filename",
      "note_content"
    ],
    "states": [
      {
        "id": "markor_main_screen",
        "desc": "Markor main file list screen with FAB button visible",
        "verify": "resource_id=net.gsantner.markor:id/fab_add_new_item"
      },
      {
        "id": "new_file_dialog_open",
        "desc": "New file creation dialog with filename input field visible",
        "verify": "resource_id=net.gsantner.markor:id/new_file_dialog__name"
      },
      {
        "id": "filename_entered",
        "desc": "New file dialog with filename typed and Markdown format selected",
        "verify": "resource_id=net.gsantner.markor:id/new_file_dialog__name"
      },
      {
        "id": "markdown_format_selected",
        "desc": "New file dialog with Markdown format chosen and OK button ready to confirm",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "note_editor_open",
        "desc": "Markor note editor screen open with empty Markdown document ready for input",
        "verify": "resource_id=net.gsantner.markor:id/document__fragment__edit_"
      },
      {
        "id": "note_content_entered",
        "desc": "Note editor with content typed and save button visible in toolbar",
        "verify": "resource_id=net.gsantner.markor:id/action_save"
      },
      {
        "id": "note_saved",
        "desc": "Note has been saved successfully; editor remains open with saved content",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "markor_main_screen",
        "to": "new_file_dialog_open",
        "action": "click resource_id=net.gsantner.markor:id/fab_add_new_item"
      },
      {
        "from": "new_file_dialog_open",
        "to": "filename_entered",
        "action": "type $filename"
      },
      {
        "from": "filename_entered",
        "to": "markdown_format_selected",
        "action": "click resource_id=android:id/text1&&text=Markdown"
      },
      {
        "from": "markdown_format_selected",
        "to": "note_editor_open",
        "action": "click resource_id=android:id/button1&&text=OK"
      },
      {
        "from": "note_editor_open",
        "to": "note_content_entered",
        "action": "type $note_content"
      },
      {
        "from": "note_content_entered",
        "to": "note_saved",
        "action": "click resource_id=net.gsantner.markor:id/action_save"
      }
    ]
  },
  {
    "task": "Create a new note in Markor named final_clever_horse.txt with the following text: The early bird catches the worm.",
    "app": "net.gsantner.markor",
    "platform": "android",
    "params": [
      "filename",
      "file_content"
    ],
    "states": [
      {
        "id": "markor_main_screen",
        "desc": "Markor main file list screen with the floating action button visible",
        "verify": "resource_id=net.gsantner.markor:id/fab_add_new_item"
      },
      {
        "id": "new_file_dialog_open",
        "desc": "New file creation dialog with filename input field visible",
        "verify": "resource_id=net.gsantner.markor:id/new_file_dialog__name"
      },
      {
        "id": "filename_entered",
        "desc": "New file dialog with filename typed and file type selector showing Plain Text option",
        "verify": "resource_id=android:id/text1&&text=Plain Text"
      },
      {
        "id": "file_type_selected",
        "desc": "New file dialog with Plain Text type selected and OK button ready to confirm",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "editor_open_empty",
        "desc": "Markor text editor open with a new empty plain text file ready for input",
        "verify": "resource_id=net.gsantner.markor:id/document__fragment__edit_"
      },
      {
        "id": "content_typed",
        "desc": "Markor text editor with file content typed and Save button visible in the toolbar",
        "verify": "resource_id=net.gsantner.markor:id/action_save"
      },
      {
        "id": "file_saved",
        "desc": "File has been saved successfully; editor remains open with the saved content",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "markor_main_screen",
        "to": "new_file_dialog_open",
        "action": "click resource_id=net.gsantner.markor:id/fab_add_new_item"
      },
      {
        "from": "new_file_dialog_open",
        "to": "filename_entered",
        "action": "type $filename"
      },
      {
        "from": "filename_entered",
        "to": "file_type_selected",
        "action": "click resource_id=android:id/text1&&text=Plain Text"
      },
      {
        "from": "file_type_selected",
        "to": "editor_open_empty",
        "action": "click resource_id=android:id/button1&&text=OK"
      },
      {
        "from": "editor_open_empty",
        "to": "content_typed",
        "action": "type $file_content"
      },
      {
        "from": "content_typed",
        "to": "file_saved",
        "action": "click resource_id=net.gsantner.markor:id/action_save"
      }
    ]
  },
  {
    "task": "In Markor, move the note 8zum_friendly_penguin.txt from WorkProjects to CodeSnippets.",
    "app": "net.gsantner.markor",
    "platform": "android",
    "params": [
      "source_folder",
      "filename",
      "destination_folder"
    ],
    "states": [
      {
        "id": "markor_home",
        "desc": "Markor main file browser screen showing list of folders and files",
        "verify": "resource_id=net.gsantner.markor:id/opoc_filesystem_item__roo"
      },
      {
        "id": "source_folder_open",
        "desc": "WorkProjects folder is open, showing its contents including the target file",
        "verify": "content_desc=File 8zum_friendly_penguin.txt "
      },
      {
        "id": "file_selected",
        "desc": "Target file is long-pressed and selected, showing contextual action bar with More options ",
        "verify": "content_desc=More options"
      },
      {
        "id": "overflow_menu_open",
        "desc": "Overflow context menu is open showing file actions including Move",
        "verify": "resource_id=net.gsantner.markor:id/title&&text=Move"
      },
      {
        "id": "move_dialog_root",
        "desc": "Move destination picker dialog is open, showing current folder contents with parent folder",
        "verify": "content_desc=Folder .. "
      },
      {
        "id": "move_dialog_parent",
        "desc": "Move destination picker navigated to parent directory, showing available destination folde",
        "verify": "content_desc=Folder CodeSnippets "
      },
      {
        "id": "destination_folder_selected",
        "desc": "CodeSnippets folder is selected as destination, showing SELECT THIS FOLDER confirmation bu",
        "verify": "resource_id=net.gsantner.markor:id/ui__filesystem_dialog__bu"
      },
      {
        "id": "move_complete",
        "desc": "File has been successfully moved to the CodeSnippets folder; task is complete",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "markor_home",
        "to": "source_folder_open",
        "action": "click content_desc=Folder WorkProjects"
      },
      {
        "from": "source_folder_open",
        "to": "file_selected",
        "action": "wait content_desc=File 8zum_friendly_penguin.txt"
      },
      {
        "from": "file_selected",
        "to": "overflow_menu_open",
        "action": "click content_desc=More options"
      },
      {
        "from": "overflow_menu_open",
        "to": "move_dialog_root",
        "action": "click resource_id=net.gsantner.markor:id/title&&text=Move"
      },
      {
        "from": "move_dialog_root",
        "to": "move_dialog_parent",
        "action": "click content_desc=Folder .."
      },
      {
        "from": "move_dialog_parent",
        "to": "destination_folder_selected",
        "action": "click content_desc=Folder CodeSnippets"
      },
      {
        "from": "destination_folder_selected",
        "to": "move_complete",
        "action": "click resource_id=net.gsantner.markor:id/ui__filesystem_dialog__bu"
      }
    ]
  },
  {
    "task": "Create a note in Markor named copy_bold_pig.txt. Perform a paste operation in the note and save the note.",
    "app": "net.gsantner.markor",
    "platform": "android",
    "params": [
      "filename"
    ],
    "states": [
      {
        "id": "markor_home",
        "desc": "Markor main file browser screen with the floating action button visible",
        "verify": "resource_id=net.gsantner.markor:id/fab_add_new_item"
      },
      {
        "id": "new_file_dialog",
        "desc": "New file or folder creation dialog with filename input field",
        "verify": "resource_id=net.gsantner.markor:id/new_file_dialog__name"
      },
      {
        "id": "filename_entered",
        "desc": "New file dialog with filename typed and file type selector showing Plain Text option",
        "verify": "resource_id=android:id/text1&&text=Plain Text"
      },
      {
        "id": "file_type_selected",
        "desc": "New file dialog with Plain Text type selected and OK button ready to confirm",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "editor_open",
        "desc": "Markor text editor open with the newly created plain text file, editor is empty",
        "verify": "resource_id=net.gsantner.markor:id/document__fragment__edit_"
      },
      {
        "id": "context_menu_open",
        "desc": "Text editor context menu visible after long press, showing Paste option",
        "verify": "content_desc=Paste"
      },
      {
        "id": "content_pasted",
        "desc": "Text editor with clipboard content pasted and Save button visible in the toolbar",
        "verify": "resource_id=net.gsantner.markor:id/action_save"
      },
      {
        "id": "file_saved",
        "desc": "File has been saved successfully; task complete",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "markor_home",
        "to": "new_file_dialog",
        "action": "click resource_id=net.gsantner.markor:id/fab_add_new_item"
      },
      {
        "from": "new_file_dialog",
        "to": "filename_entered",
        "action": "type $filename"
      },
      {
        "from": "filename_entered",
        "to": "file_type_selected",
        "action": "click resource_id=android:id/text1&&text=Plain Text"
      },
      {
        "from": "file_type_selected",
        "to": "editor_open",
        "action": "click resource_id=android:id/button1&&text=OK"
      },
      {
        "from": "editor_open",
        "to": "context_menu_open",
        "action": "wait resource_id=net.gsantner.markor:id/document__fragment__edit_"
      },
      {
        "from": "context_menu_open",
        "to": "content_pasted",
        "action": "click content_desc=Paste"
      },
      {
        "from": "content_pasted",
        "to": "file_saved",
        "action": "click resource_id=net.gsantner.markor:id/action_save"
      }
    ]
  },
  {
    "task": "Delete all my notes in Markor.",
    "app": "net.gsantner.markor",
    "platform": "android",
    "params": [],
    "states": [
      {
        "id": "markor_home",
        "desc": "Markor main file browser screen showing list of markdown files",
        "verify": "resource_id=net.gsantner.markor:id/opoc_filesystem_item__roo"
      },
      {
        "id": "first_file_selected",
        "desc": "Markor file browser in multi-select mode after long-pressing the first file (2023_02_03_me",
        "verify": "resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "id": "second_file_selected",
        "desc": "Multi-select mode with two files selected including 2023_09_09_grocery_list_weekly.md",
        "verify": "resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "id": "third_file_selected",
        "desc": "Multi-select mode with three files selected including 9r5p_summer_vacation_plans.md",
        "verify": "resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "id": "fourth_file_selected",
        "desc": "Multi-select mode with four files selected including art_project_sketches_copy.md",
        "verify": "resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "id": "fifth_file_selected",
        "desc": "Multi-select mode with five files selected including budget_home_renovation_final.md",
        "verify": "resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "id": "sixth_file_selected",
        "desc": "Multi-select mode with six files selected including fW01A_backup.md",
        "verify": "resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "id": "delete_confirmation_dialog",
        "desc": "Delete confirmation dialog asking user to confirm deletion of selected files",
        "verify": "resource_id=android:id/button1&&text=OK"
      },
      {
        "id": "files_deleted",
        "desc": "Files successfully deleted and Markor returns to the file browser with the selected files ",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "markor_home",
        "to": "first_file_selected",
        "action": "click content_desc=File 2023_02_03_meeting_notes_project_team.md"
      },
      {
        "from": "first_file_selected",
        "to": "second_file_selected",
        "action": "click content_desc=File 2023_09_09_grocery_list_weekly.md"
      },
      {
        "from": "second_file_selected",
        "to": "third_file_selected",
        "action": "click content_desc=File 9r5p_summer_vacation_plans.md"
      },
      {
        "from": "third_file_selected",
        "to": "fourth_file_selected",
        "action": "click content_desc=File art_project_sketches_copy.md"
      },
      {
        "from": "fourth_file_selected",
        "to": "fifth_file_selected",
        "action": "click content_desc=File budget_home_renovation_final.md"
      },
      {
        "from": "fifth_file_selected",
        "to": "sixth_file_selected",
        "action": "click content_desc=File fW01A_backup.md"
      },
      {
        "from": "sixth_file_selected",
        "to": "delete_confirmation_dialog",
        "action": "click resource_id=net.gsantner.markor:id/action_delete_selected_it"
      },
      {
        "from": "delete_confirmation_dialog",
        "to": "files_deleted",
        "action": "click resource_id=android:id/button1&&text=OK"
      }
    ]
  },
  {
    "task": "Add a favorite location marker for 47.0688832, 9.5061564 in the OsmAnd maps app.",
    "app": "net.osmand",
    "platform": "android",
    "params": [
      "coordinates",
      "favorite_name"
    ],
    "states": [
      {
        "id": "osmand_map_main",
        "desc": "OsmAnd main map screen with search button visible",
        "verify": "resource_id=net.osmand:id/map_search_button"
      },
      {
        "id": "search_screen_open",
        "desc": "OsmAnd search screen with text input field active",
        "verify": "resource_id=net.osmand:id/searchEditText"
      },
      {
        "id": "coordinates_entered",
        "desc": "Map view showing the searched coordinates location after navigating back to map",
        "verify": "resource_id=net.osmand:id/MapLayersView"
      },
      {
        "id": "map_focused_on_location",
        "desc": "Map view centered on the target coordinates, ready for long press",
        "verify": "resource_id=net.osmand:id/MapLayersView"
      },
      {
        "id": "context_menu_open",
        "desc": "Map context menu open after long press, showing options including Add favorite",
        "verify": "resource_id=net.osmand:id/text&&text=Add"
      },
      {
        "id": "add_favorite_dialog",
        "desc": "Add favorite dialog with name input field visible",
        "verify": "resource_id=net.osmand:id/name_edit"
      },
      {
        "id": "favorite_name_entered",
        "desc": "Add favorite dialog with name filled in and Save button ready to tap",
        "verify": "resource_id=net.osmand:id/button_text&&text=Save"
      },
      {
        "id": "favorite_saved_terminal",
        "desc": "Favorite/waypoint successfully saved at the specified coordinates with the given name",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "osmand_map_main",
        "to": "search_screen_open",
        "action": "click resource_id=net.osmand:id/map_search_button"
      },
      {
        "from": "search_screen_open",
        "to": "coordinates_entered",
        "action": "type $coordinates"
      },
      {
        "from": "coordinates_entered",
        "to": "map_focused_on_location",
        "action": "click resource_id=net.osmand:id/MapLayersView"
      },
      {
        "from": "map_focused_on_location",
        "to": "context_menu_open",
        "action": "wait resource_id=net.osmand:id/MapLayersView"
      },
      {
        "from": "context_menu_open",
        "to": "add_favorite_dialog",
        "action": "click resource_id=net.osmand:id/text&&text=Add"
      },
      {
        "from": "add_favorite_dialog",
        "to": "favorite_name_entered",
        "action": "type $favorite_name"
      },
      {
        "from": "favorite_name_entered",
        "to": "favorite_saved_terminal",
        "action": "click resource_id=net.osmand:id/button_text&&text=Save"
      }
    ]
  },
  {
    "task": "Could you tone down the brightness of my photo?",
    "app": "GIMP",
    "platform": "desktop",
    "params": [
      "brightness_value"
    ],
    "states": [
      {
        "id": "gimp_main_window",
        "desc": "GIMP main window with the image open and the menu bar visible",
        "verify": "role=menu&&name=Colors"
      },
      {
        "id": "colors_menu_open",
        "desc": "Colors menu is open showing Brightness-Contrast menu item",
        "verify": "role=menu item&&name=Brightness-Contrast"
      },
      {
        "id": "brightness_contrast_dialog",
        "desc": "Brightness-Contrast dialog is open with spin-button fields for brightness and contrast",
        "verify": "role=push-button&&name=OK"
      },
      {
        "id": "brightness_value_entered",
        "desc": "Brightness value has been typed into the spin-button field and Tab pressed to confirm",
        "verify": "role=push-button&&name=OK"
      },
      {
        "id": "adjustment_applied",
        "desc": "Brightness-Contrast dialog closed and adjustment applied; GIMP main window is active",
        "verify": "role=menu&&name=File"
      },
      {
        "id": "file_menu_open",
        "desc": "File menu is open showing available file operations",
        "verify": "role=label&&name=Brightness-Contrast"
      },
      {
        "id": "terminal",
        "desc": "Task complete — Brightness-Contrast adjustment applied and File menu interaction finished",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "gimp_main_window",
        "to": "colors_menu_open",
        "action": "click role=menu&&name=Colors"
      },
      {
        "from": "colors_menu_open",
        "to": "brightness_contrast_dialog",
        "action": "click role=menu item&&name=Brightness-Contrast"
      },
      {
        "from": "brightness_contrast_dialog",
        "to": "brightness_value_entered",
        "action": "type $brightness_value"
      },
      {
        "from": "brightness_value_entered",
        "to": "adjustment_applied",
        "action": "press Tab"
      },
      {
        "from": "adjustment_applied",
        "to": "file_menu_open",
        "action": "click role=push-button&&name=OK"
      },
      {
        "from": "file_menu_open",
        "to": "terminal",
        "action": "click role=menu&&name=File"
      }
    ]
  },
  {
    "task": "Could you assist me in enhancing the color vibrancy of my photo?",
    "app": "GIMP",
    "platform": "desktop",
    "params": [
      "spin_value"
    ],
    "states": [
      {
        "id": "gimp_main_window",
        "desc": "GIMP main window with the image open",
        "verify": "role=frame&&name=[woman_sitting_by_the_tree2] (imported)-1.0"
      },
      {
        "id": "colors_menu_open_first",
        "desc": "Colors menu is open in GIMP",
        "verify": "role=menu&&name=Colors"
      },
      {
        "id": "image_frame_focused",
        "desc": "GIMP image frame is focused after first Colors menu interaction",
        "verify": "role=frame&&name=[woman_sitting_by_the_tree2] (imported)-1.0"
      },
      {
        "id": "colors_menu_open_second",
        "desc": "Colors menu is open again to select a color adjustment tool",
        "verify": "role=menu&&name=Colors"
      },
      {
        "id": "color_adjustment_dialog",
        "desc": "Color adjustment dialog (e.g., Hue-Saturation or Brightness-Contrast) is open with a spin ",
        "verify": "role=spin-button&&name=0.0"
      },
      {
        "id": "spin_value_entered",
        "desc": "Spin button value has been set and Tab pressed; OK button is available",
        "verify": "role=push-button&&name=OK"
      },
      {
        "id": "dialog_confirmed",
        "desc": "Color adjustment dialog closed; back to GIMP main window",
        "verify": "role=frame&&name=[woman_sitting_by_the_tree2] (imported)-1.0"
      },
      {
        "id": "file_menu_open",
        "desc": "File menu is open in GIMP",
        "verify": "role=menu&&name=File"
      },
      {
        "id": "terminal",
        "desc": "GEGL Operation item has been clicked in the File menu; task complete",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "gimp_main_window",
        "to": "colors_menu_open_first",
        "action": "click role=menu&&name=Colors"
      },
      {
        "from": "colors_menu_open_first",
        "to": "image_frame_focused",
        "action": "click role=frame&&name=[woman_sitting_by_the_tree2] (imported)-1.0"
      },
      {
        "from": "image_frame_focused",
        "to": "colors_menu_open_second",
        "action": "click role=menu&&name=Colors"
      },
      {
        "from": "colors_menu_open_second",
        "to": "color_adjustment_dialog",
        "action": "click role=spin-button&&name=0.0"
      },
      {
        "from": "color_adjustment_dialog",
        "to": "spin_value_entered",
        "action": "click role=spin-button&&name=0.0"
      },
      {
        "from": "spin_value_entered",
        "to": "dialog_confirmed",
        "action": "type $spin_value"
      },
      {
        "from": "dialog_confirmed",
        "to": "file_menu_open",
        "action": "click role=push-button&&name=OK"
      },
      {
        "from": "file_menu_open",
        "to": "terminal",
        "action": "click role=menu&&name=File"
      }
    ]
  },
  {
    "task": "Can you make Bing the main search engine when I look stuff up on the internet?",
    "app": "Google Chrome",
    "platform": "desktop",
    "params": [],
    "states": [
      {
        "id": "chrome_open",
        "desc": "Google Chrome browser open with address bar visible",
        "verify": "name='Address and search bar'&&role=OmniboxViewViews"
      },
      {
        "id": "search_engine_settings",
        "desc": "Chrome search engine settings page showing list of search engines including Microsoft Bing",
        "verify": "name='More actions for Microsoft Bing'&&role=icon-more-vert"
      },
      {
        "id": "bing_actions_menu_open",
        "desc": "Dropdown actions menu open for Microsoft Bing with 'Make default' option visible",
        "verify": "name='Make default'&&role=dropdown-item"
      },
      {
        "id": "bing_set_as_default",
        "desc": "Microsoft Bing has been set as the default search engine in Chrome",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "chrome_open",
        "to": "search_engine_settings",
        "action": "type \"chrome://settings/search\n\""
      },
      {
        "from": "search_engine_settings",
        "to": "bing_actions_menu_open",
        "action": "click name='More actions for Microsoft Bing'&&role=icon-more-vert"
      },
      {
        "from": "bing_actions_menu_open",
        "to": "bing_set_as_default",
        "action": "click name='Make default'&&role=dropdown-item"
      }
    ]
  },
  {
    "task": "Hey, I need a quick way back to this site. Could you whip up a shortcut on my desktop for me using Chrome's built-in feature?",
    "app": "Google Chrome",
    "platform": "desktop",
    "params": [],
    "states": [
      {
        "id": "chrome_browser_open",
        "desc": "Google Chrome browser is open with the app menu button visible in the toolbar",
        "verify": "role=BrowserAppMenuButton"
      },
      {
        "id": "app_menu_open",
        "desc": "Chrome application menu is open showing top-level menu items including 'More tools'",
        "verify": "role=MenuItemView&&name=More tools"
      },
      {
        "id": "more_tools_submenu_open",
        "desc": "More tools submenu is open showing options including 'Cast, save and share'",
        "verify": "role=MenuItemView&&name=Cast, save and share"
      },
      {
        "id": "cast_save_share_submenu_open",
        "desc": "Cast, save and share submenu is open showing the 'Create shortcut…' option",
        "verify": "role=MenuItemView&&name=Create shortcut…"
      },
      {
        "id": "create_shortcut_dialog_open",
        "desc": "Create shortcut dialog is open with a 'Create' button ready to confirm shortcut creation",
        "verify": "role=MdTextButton&&name=Create"
      },
      {
        "id": "shortcut_created",
        "desc": "Desktop shortcut has been successfully created and the dialog has closed",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "chrome_browser_open",
        "to": "app_menu_open",
        "action": "click role=BrowserAppMenuButton"
      },
      {
        "from": "app_menu_open",
        "to": "more_tools_submenu_open",
        "action": "click role=MenuItemView&&name=More tools"
      },
      {
        "from": "more_tools_submenu_open",
        "to": "cast_save_share_submenu_open",
        "action": "click role=MenuItemView&&name=Cast, save and share"
      },
      {
        "from": "cast_save_share_submenu_open",
        "to": "create_shortcut_dialog_open",
        "action": "click role=MenuItemView&&name=Create shortcut…"
      },
      {
        "from": "create_shortcut_dialog_open",
        "to": "shortcut_created",
        "action": "click role=MdTextButton&&name=Create"
      }
    ]
  },
  {
    "task": "Can you help me clean up my computer by getting rid of all the tracking things that Amazon might have saved? I want to make sure my browsing is private and those sites don't remember me.",
    "app": "Google Chrome / Chromium Browser",
    "platform": "desktop",
    "params": [],
    "states": [
      {
        "id": "browser_open",
        "desc": "Browser is open with any page active",
        "verify": "role=document-web"
      },
      {
        "id": "clear_browsing_data_dialog",
        "desc": "Clear browsing data dialog is open, showing the Basic tab by default",
        "verify": "name=Advanced&&role=static"
      },
      {
        "id": "advanced_tab_active",
        "desc": "Advanced tab of the Clear browsing data dialog is active, showing the Time range selector",
        "verify": "name=Time range&&role=md-select"
      },
      {
        "id": "time_range_dropdown_open",
        "desc": "Time range dropdown menu is open with options including 'All time'",
        "verify": "name=All time&&role=menu-item"
      },
      {
        "id": "all_time_selected",
        "desc": "All time is selected as the time range; the Delete data button is visible after scrolling",
        "verify": "name=Delete data&&role=static"
      },
      {
        "id": "data_cleared",
        "desc": "Browsing data has been deleted and the dialog has closed, returning to the Privacy and sec",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "browser_open",
        "to": "clear_browsing_data_dialog",
        "action": "press ctrl+shift+Delete"
      },
      {
        "from": "clear_browsing_data_dialog",
        "to": "advanced_tab_active",
        "action": "click name=Advanced&&role=static"
      },
      {
        "from": "advanced_tab_active",
        "to": "time_range_dropdown_open",
        "action": "click name=Time range&&role=md-select"
      },
      {
        "from": "time_range_dropdown_open",
        "to": "all_time_selected",
        "action": "click name=All time&&role=menu-item"
      },
      {
        "from": "all_time_selected",
        "to": "all_time_selected",
        "action": "scroll"
      },
      {
        "from": "all_time_selected",
        "to": "data_cleared",
        "action": "click name=Delete data&&role=static"
      }
    ]
  },
  {
    "task": "Check the names in column \"Names with duplicates\" and put the unique ones in column \"Unique Names\". Keep the original order of the first occurrences. Finish the work and don't touch irrelevant regions, even if they are blank.",
    "app": "LibreOffice Calc",
    "platform": "desktop",
    "params": [
      "names_list"
    ],
    "states": [
      {
        "id": "calc_open",
        "desc": "LibreOffice Calc spreadsheet is open and ready for editing",
        "verify": "role=table-cell&&name=B2"
      },
      {
        "id": "cell_d1_selected",
        "desc": "Cell D1 is selected in the spreadsheet",
        "verify": "role=table-cell&&name=D1"
      },
      {
        "id": "cell_d2_selected",
        "desc": "Cell D2 is selected and ready for data entry",
        "verify": "role=table-cell&&name=D2"
      },
      {
        "id": "data_entered",
        "desc": "Names list has been typed into cells starting at D2, each name on a new row",
        "verify": "role=table-cell&&name=D2"
      },
      {
        "id": "save_dialog_open",
        "desc": "Keep Current Format dialog is open asking whether to save in the existing format",
        "verify": "role=push button&&name=Keep Current Format"
      },
      {
        "id": "file_saved",
        "desc": "File has been saved successfully in its current format and the spreadsheet is active",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "calc_open",
        "to": "cell_d1_selected",
        "action": "click role=table-cell&&name=D1"
      },
      {
        "from": "cell_d1_selected",
        "to": "cell_d2_selected",
        "action": "click role=table-cell&&name=D2"
      },
      {
        "from": "cell_d2_selected",
        "to": "data_entered",
        "action": "type $names_list"
      },
      {
        "from": "data_entered",
        "to": "save_dialog_open",
        "action": "press ctrl+s"
      },
      {
        "from": "save_dialog_open",
        "to": "file_saved",
        "action": "press Return"
      }
    ]
  },
  {
    "task": "Compute the sum of \"Revenue\" and \"Total Expenses\" and put the results under two columns named \"Total Revenue\" and \"Total Expenses\" of a new sheet (Sheet2)",
    "app": "LibreOffice Calc",
    "platform": "desktop",
    "params": [],
    "states": [
      {
        "id": "calc_open",
        "desc": "LibreOffice Calc is open with Sheet1 tab visible",
        "verify": "role=page-tab&&name=Sheet1"
      },
      {
        "id": "at_home_cell",
        "desc": "Cursor is at cell A1 (home position) in the current sheet",
        "verify": "role=table-cell&&name=A1"
      },
      {
        "id": "sheet1_context_menu_open",
        "desc": "Right-click context menu on Sheet1 tab is open",
        "verify": "role=menu item&&name=Insert Sheet"
      },
      {
        "id": "summary_sheet_active",
        "desc": "A summary/new sheet is active and cell N28 is visible (confirming sheet navigation complet",
        "verify": "role=table-cell&&name=N28"
      },
      {
        "id": "cell_a1_selected",
        "desc": "Cell A1 is selected on the summary sheet, ready for data entry",
        "verify": "role=table-cell&&name=A1"
      },
      {
        "id": "data_entered",
        "desc": "Headers and SUM formulas have been typed; cursor is now at A2 after entry",
        "verify": "role=table-cell&&name=A2"
      },
      {
        "id": "file_saved",
        "desc": "File has been saved (Ctrl+S issued); spreadsheet remains open at A2",
        "verify": "role=table-cell&&name=A2"
      },
      {
        "id": "terminal",
        "desc": "Task complete: summary sheet populated with headers and SUM formulas, file saved",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "calc_open",
        "to": "at_home_cell",
        "action": "press ctrl+Home"
      },
      {
        "from": "at_home_cell",
        "to": "sheet1_context_menu_open",
        "action": "click role=page-tab&&name=Sheet1"
      },
      {
        "from": "sheet1_context_menu_open",
        "to": "summary_sheet_active",
        "action": "click role=table-cell&&name=N28"
      },
      {
        "from": "summary_sheet_active",
        "to": "cell_a1_selected",
        "action": "click role=table-cell&&name=A1"
      },
      {
        "from": "cell_a1_selected",
        "to": "data_entered",
        "action": "type \"Total Revenue\tTotal Expenses\n=SUM(Sheet1\""
      },
      {
        "from": "data_entered",
        "to": "file_saved",
        "action": "press ctrl+s"
      },
      {
        "from": "file_saved",
        "to": "terminal",
        "action": "click role=table-cell&&name=A2"
      }
    ]
  },
  {
    "task": "Make the line spacing of first two paragraph into double line spacing",
    "app": "LibreOffice Writer",
    "platform": "desktop",
    "params": [],
    "states": [
      {
        "id": "document_open",
        "desc": "LibreOffice Writer document is open with the target paragraphs visible",
        "verify": "name='Compared to a short story, a novel has main characters"
      },
      {
        "id": "paragraphs_selected",
        "desc": "Two paragraphs are selected from the first paragraph through the second paragraph",
        "verify": "name='A novel may have any number of climaxes, each perhaps "
      },
      {
        "id": "format_menu_open",
        "desc": "Format menu is open showing Paragraph menu item",
        "verify": "name='Paragraph...'&&role=menu-item"
      },
      {
        "id": "paragraph_dialog_open",
        "desc": "Paragraph formatting dialog is open with Line Spacing panel visible",
        "verify": "name='Line Spacing'&&role=panel"
      },
      {
        "id": "double_spacing_selected",
        "desc": "Double line spacing option is selected in the Line Spacing panel",
        "verify": "name='Double'&&role=table-cell"
      },
      {
        "id": "dialog_closed",
        "desc": "Paragraph dialog has been closed and document is back in focus",
        "verify": "name='Format'&&role=menu"
      },
      {
        "id": "file_saved",
        "desc": "Document has been saved successfully",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "document_open",
        "to": "paragraphs_selected",
        "action": "click name='Compared to a short story, a novel has main characters"
      },
      {
        "from": "paragraphs_selected",
        "to": "format_menu_open",
        "action": "click name='A novel may have any number of climaxes, each perhaps"
      },
      {
        "from": "format_menu_open",
        "to": "paragraph_dialog_open",
        "action": "click name='Format'&&role=menu"
      },
      {
        "from": "paragraph_dialog_open",
        "to": "double_spacing_selected",
        "action": "click name='Paragraph...'&&role=menu-item"
      },
      {
        "from": "double_spacing_selected",
        "to": "dialog_closed",
        "action": "click name='Line Spacing'&&role=panel"
      },
      {
        "from": "dialog_closed",
        "to": "file_saved",
        "action": "click name='Double'&&role=table-cell"
      },
      {
        "from": "file_saved",
        "to": "document_open",
        "action": "click name='OK'&&role=push-button"
      }
    ]
  },
  {
    "task": "Help me to remove the account \"anonym-x2024@outlook.com\"",
    "app": "Mozilla Thunderbird",
    "platform": "desktop",
    "params": [],
    "states": [
      {
        "id": "thunderbird_main",
        "desc": "Thunderbird main window with Account Settings link visible in the toolbar or sidebar",
        "verify": "name=Account Settings&&role=btn-link"
      },
      {
        "id": "account_settings_open",
        "desc": "Account Settings tab open showing the list of accounts and the Account Actions button",
        "verify": "name=Account Actions&&role=push-button"
      },
      {
        "id": "account_actions_menu_open",
        "desc": "Account Actions dropdown menu open with Remove Account option visible",
        "verify": "name=Remove Account&&role=menu-item"
      },
      {
        "id": "remove_account_confirm_dialog",
        "desc": "Confirmation dialog asking whether to remove the account, with a Remove button",
        "verify": "name=Remove&&role=push-button"
      },
      {
        "id": "remove_account_final_dialog",
        "desc": "Final confirmation or success dialog with an OK button after account removal",
        "verify": "name=OK&&role=push-button"
      },
      {
        "id": "account_removed_done",
        "desc": "Account has been successfully removed; Thunderbird returns to the main or account settings",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "thunderbird_main",
        "to": "account_settings_open",
        "action": "click name=Account Settings&&role=btn-link"
      },
      {
        "from": "account_settings_open",
        "to": "account_actions_menu_open",
        "action": "click name=Account Actions&&role=push-button"
      },
      {
        "from": "account_actions_menu_open",
        "to": "remove_account_confirm_dialog",
        "action": "click name=Remove Account&&role=menu-item"
      },
      {
        "from": "remove_account_confirm_dialog",
        "to": "remove_account_final_dialog",
        "action": "click name=Remove&&role=push-button"
      },
      {
        "from": "remove_account_final_dialog",
        "to": "account_removed_done",
        "action": "click name=OK&&role=push-button"
      }
    ]
  },
  {
    "task": "I am currently using an Ubuntu system, and I have wrongly deleted a poster of party night. Could you help me recover it from the Trash?",
    "app": "Nautilus Files (Trash)",
    "platform": "desktop",
    "params": [
      "file_name"
    ],
    "states": [
      {
        "id": "desktop_ready",
        "desc": "Ubuntu desktop with the Trash icon visible in the taskbar/dock",
        "verify": "name=Trash&&role=push-button"
      },
      {
        "id": "trash_window_open",
        "desc": "Nautilus Trash window open showing deleted files including the target file",
        "verify": "name=poster_party_night.webp&&role=canvas"
      },
      {
        "id": "file_selected",
        "desc": "Target file selected in Trash window with the Restore button visible in the toolbar",
        "verify": "name=Restore&&role=push-button"
      },
      {
        "id": "file_restored",
        "desc": "File has been restored from Trash to its original location; task complete",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "desktop_ready",
        "to": "trash_window_open",
        "action": "click name=Trash&&role=push-button"
      },
      {
        "from": "trash_window_open",
        "to": "file_selected",
        "action": "click name=poster_party_night.webp&&role=canvas"
      },
      {
        "from": "file_selected",
        "to": "file_restored",
        "action": "click name=Restore&&role=push-button"
      }
    ]
  },
  {
    "task": "When I ran \"conda install datasets\" in terminal, I got \"conda: command not found\". Could you help me solve it so that I can use conda command right away?",
    "app": "Terminal",
    "platform": "desktop",
    "params": [],
    "states": [
      {
        "id": "terminal_open",
        "desc": "Terminal window is open and ready for input",
        "verify": "role=terminal"
      },
      {
        "id": "miniconda_downloaded",
        "desc": "Terminal after curl download command has been entered; Miniconda installer script is being",
        "verify": "role=terminal"
      },
      {
        "id": "miniconda_installed",
        "desc": "Terminal after running the Miniconda bash installer silently into $HOME/miniconda3",
        "verify": "role=terminal"
      },
      {
        "id": "conda_init_done",
        "desc": "Terminal after conda init bash has been run, modifying ~/.bashrc for conda shell integrati",
        "verify": "role=terminal"
      },
      {
        "id": "bashrc_sourced",
        "desc": "Terminal after sourcing ~/.bashrc to apply conda initialization in the current shell sessi",
        "verify": "role=terminal"
      },
      {
        "id": "conda_version_checked",
        "desc": "Terminal after running 'conda --version', displaying the installed conda version",
        "verify": "role=terminal"
      },
      {
        "id": "conda_version_captured",
        "desc": "Conda version string has been read from the terminal output",
        "verify": "data_available"
      },
      {
        "id": "done",
        "desc": "Miniconda installation complete and conda version verified; task finished",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "terminal_open",
        "to": "miniconda_downloaded",
        "action": "type \"curl -sL https://repo.anaconda.com/minic\""
      },
      {
        "from": "miniconda_downloaded",
        "to": "miniconda_installed",
        "action": "type \"bash /tmp/miniconda.sh -b -p $HOME/minic\""
      },
      {
        "from": "miniconda_installed",
        "to": "conda_init_done",
        "action": "type \"$HOME/miniconda3/bin/conda init bash\n\""
      },
      {
        "from": "conda_init_done",
        "to": "bashrc_sourced",
        "action": "type \"source ~/.bashrc\n\""
      },
      {
        "from": "bashrc_sourced",
        "to": "conda_version_checked",
        "action": "type \"conda --version\n\""
      },
      {
        "from": "conda_version_checked",
        "to": "conda_version_captured",
        "action": "inspect_text role=terminal"
      },
      {
        "from": "conda_version_captured",
        "to": "done",
        "action": "wait"
      }
    ]
  },
  {
    "task": "I remember there is a file named \"secret.docx\" on this computer, but I can't remember where it is. Please find the path where this file is stored and copy it to the clipboard.",
    "app": "Terminal (bash)",
    "platform": "desktop",
    "params": [
      "file_name",
      "file_path"
    ],
    "states": [
      {
        "id": "desktop_ready",
        "desc": "Ubuntu desktop is ready and visible",
        "verify": "role=desktop"
      },
      {
        "id": "terminal_open",
        "desc": "Terminal window is open and ready for input",
        "verify": "role=terminal"
      },
      {
        "id": "find_command_issued",
        "desc": "Terminal after running find command to locate secret.docx",
        "verify": "role=terminal"
      },
      {
        "id": "xclip_install_started",
        "desc": "Terminal after issuing sudo apt install xclip command, waiting for password prompt",
        "verify": "role=terminal"
      },
      {
        "id": "sudo_password_entered_first",
        "desc": "Terminal after entering sudo password the first time",
        "verify": "role=terminal"
      },
      {
        "id": "sudo_password_entered_second",
        "desc": "Terminal after entering sudo password the second time, xclip installation in progress",
        "verify": "role=terminal"
      },
      {
        "id": "xclip_install_interrupted",
        "desc": "Terminal after Ctrl+C interrupts the xclip install or previous command",
        "verify": "role=terminal"
      },
      {
        "id": "xsel_copy_issued",
        "desc": "Terminal after running xsel command to copy file path to clipboard",
        "verify": "role=terminal"
      },
      {
        "id": "clipboard_verified",
        "desc": "Terminal after verifying clipboard contents with xsel --clipboard --output",
        "verify": "role=terminal"
      },
      {
        "id": "task_complete",
        "desc": "Task complete: the file path '/home/user/Data3/List3/secret.docx' has been copied to the c",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "desktop_ready",
        "to": "terminal_open",
        "action": "press ctrl+alt+t"
      },
      {
        "from": "terminal_open",
        "to": "find_command_issued",
        "action": "type \"find / -name \"secret.docx\" 2>/dev/null\n\""
      },
      {
        "from": "find_command_issued",
        "to": "xclip_install_started",
        "action": "type \"sudo apt install -y xclip\n\""
      },
      {
        "from": "xclip_install_started",
        "to": "sudo_password_entered_first",
        "action": "type \"osworld-public-evaluation\n\""
      },
      {
        "from": "sudo_password_entered_first",
        "to": "sudo_password_entered_second",
        "action": "type \"osworld-public-evaluation\n\""
      },
      {
        "from": "sudo_password_entered_second",
        "to": "xclip_install_interrupted",
        "action": "press ctrl+c"
      },
      {
        "from": "xclip_install_interrupted",
        "to": "xsel_copy_issued",
        "action": "type \"echo -n \"/home/user/Data3/List3/secret.d\""
      },
      {
        "from": "xsel_copy_issued",
        "to": "clipboard_verified",
        "action": "type \"xsel --clipboard --output\n\""
      },
      {
        "from": "clipboard_verified",
        "to": "task_complete",
        "action": "inspect_text role=terminal"
      }
    ]
  },
  {
    "task": "Hey, my LibreOffice Writer seems to have frozen and I can't get it to close normally. Can you help me force quit the application from the command line? I'm on Ubuntu and I don't want to restart my computer or lose any other work I have open.",
    "app": "Terminal / Desktop",
    "platform": "desktop",
    "params": [],
    "states": [
      {
        "id": "desktop_visible",
        "desc": "Desktop is visible with a background image",
        "verify": "role=image&&name=Picture 7"
      },
      {
        "id": "terminal_open",
        "desc": "Terminal or notification bar is open and accessible",
        "verify": "role=label&&name=Software updates are waiting and ready to b"
      },
      {
        "id": "pgrep_first_run",
        "desc": "Terminal after running 'pgrep -a soffice' to find LibreOffice process IDs",
        "verify": "role=terminal"
      },
      {
        "id": "kill_issued",
        "desc": "Terminal after issuing 'kill -9 <pid>' to terminate the specific soffice process",
        "verify": "role=terminal"
      },
      {
        "id": "pkill_issued",
        "desc": "Terminal after issuing 'pkill -9 -f soffice' to kill any remaining soffice processes",
        "verify": "role=terminal"
      },
      {
        "id": "pgrep_verify",
        "desc": "Terminal after running 'pgrep -a soffice' again to verify no soffice processes remain",
        "verify": "role=terminal"
      },
      {
        "id": "task_complete",
        "desc": "All LibreOffice processes have been killed and verified as gone",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "desktop_visible",
        "to": "terminal_open",
        "action": "click role=label&&name=Software updates are waiting and ready to b"
      },
      {
        "from": "terminal_open",
        "to": "pgrep_first_run",
        "action": "type \"pgrep -a soffice\n\""
      },
      {
        "from": "pgrep_first_run",
        "to": "kill_issued",
        "action": "type \"kill -9 323\n\""
      },
      {
        "from": "kill_issued",
        "to": "pkill_issued",
        "action": "type \"pkill -9 -f soffice\n\""
      },
      {
        "from": "pkill_issued",
        "to": "pgrep_verify",
        "action": "type \"pgrep -a soffice\n\""
      },
      {
        "from": "pgrep_verify",
        "to": "task_complete",
        "action": "wait"
      }
    ]
  },
  {
    "task": "Could you start VS Code in folder ~/Desktop/project from the terminal?",
    "app": "Terminal / VS Code",
    "platform": "desktop",
    "params": [
      "project_path"
    ],
    "states": [
      {
        "id": "desktop_ready",
        "desc": "Ubuntu desktop is visible with a software-update notification label in the top bar",
        "verify": "role=label&&name=Software updates are waiting and ready to b"
      },
      {
        "id": "terminal_open",
        "desc": "A terminal window is open and ready to accept commands",
        "verify": "role=terminal&&name=Terminal"
      },
      {
        "id": "vscode_launched",
        "desc": "Visual Studio Code has been launched with the specified project folder open",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "desktop_ready",
        "to": "terminal_open",
        "action": "click role=terminal&&name=Terminal"
      },
      {
        "from": "terminal_open",
        "to": "vscode_launched",
        "action": "type $project_path"
      }
    ]
  },
  {
    "task": "Please help me change all the places in this document that say \"text\" to \"test\".",
    "app": "Text Editor (gedit or similar)",
    "platform": "desktop",
    "params": [
      "find_text",
      "replace_text"
    ],
    "states": [
      {
        "id": "editor_open",
        "desc": "Text editor is open with a document ready for editing",
        "verify": "role=text editor"
      },
      {
        "id": "find_replace_dialog_open",
        "desc": "Find and Replace dialog is open with the Find input field visible",
        "verify": "name=Find&&role=input"
      },
      {
        "id": "find_text_entered",
        "desc": "Find field has been filled with the search term and Replace field is focused",
        "verify": "name=Replace&&role=input"
      },
      {
        "id": "replace_text_entered",
        "desc": "Replace field has been filled with the replacement term",
        "verify": "name=Replace&&role=input"
      },
      {
        "id": "replacement_applied",
        "desc": "Replace All action has been triggered and replacements have been applied",
        "verify": "role=section"
      },
      {
        "id": "file_saved",
        "desc": "File has been saved successfully and the editor is in a clean state",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "editor_open",
        "to": "find_replace_dialog_open",
        "action": "press ctrl+h"
      },
      {
        "from": "find_replace_dialog_open",
        "to": "find_text_entered",
        "action": "type $find_text"
      },
      {
        "from": "find_text_entered",
        "to": "replace_text_entered",
        "action": "type $replace_text"
      },
      {
        "from": "replace_text_entered",
        "to": "replacement_applied",
        "action": "click role=section"
      },
      {
        "from": "replacement_applied",
        "to": "file_saved",
        "action": "press ctrl+s"
      }
    ]
  },
  {
    "task": "Please help me use VS Code to open the \"project\" in the \"user\" folder under \"home\".",
    "app": "Visual Studio Code",
    "platform": "desktop",
    "params": [
      "folder_path"
    ],
    "states": [
      {
        "id": "vscode_open",
        "desc": "Visual Studio Code is open with a workspace or welcome screen visible",
        "verify": "name=Software&&role=frame"
      },
      {
        "id": "file_menu_open",
        "desc": "File menu is expanded showing options including Open Folder",
        "verify": "name=Open Folder&&role=monaco-button monaco-text-button"
      },
      {
        "id": "open_folder_dialog",
        "desc": "Open Folder dialog or file picker is displayed for selecting a folder",
        "verify": "name=Settings Table of Contents&&role=monaco-list list_id_1 "
      },
      {
        "id": "folder_opened",
        "desc": "The selected folder has been opened in Visual Studio Code and is visible in the editor",
        "verify": "name=Settings - Visual Studio Code&&role=document-web"
      },
      {
        "id": "terminal_done",
        "desc": "Task complete — folder is open in Visual Studio Code",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "vscode_open",
        "to": "file_menu_open",
        "action": "click name=File&&role=MenuButton"
      },
      {
        "from": "file_menu_open",
        "to": "open_folder_dialog",
        "action": "click name=Open Folder&&role=monaco-button monaco-text-button"
      },
      {
        "from": "open_folder_dialog",
        "to": "folder_opened",
        "action": "click name=Settings Table of Contents&&role=monaco-list list_id_1"
      },
      {
        "from": "folder_opened",
        "to": "terminal_done",
        "action": "click name=Settings - Visual Studio Code&&role=document-web"
      }
    ]
  },
  {
    "task": "Please help me set the current user's line length for code wrapping to 50 characters in VS Code.",
    "app": "Visual Studio Code",
    "platform": "desktop",
    "params": [
      "word_wrap_column_value"
    ],
    "states": [
      {
        "id": "vscode_settings_open",
        "desc": "VS Code Settings tab is open and visible",
        "verify": "name=Settings - Visual Studio Code&&role=document-web"
      },
      {
        "id": "search_box_focused",
        "desc": "VS Code Settings search box is focused and ready for input",
        "verify": "name=Settings - Visual Studio Code&&role=document-web"
      },
      {
        "id": "search_results_shown",
        "desc": "Settings search results showing the editor.wordWrapColumn input field",
        "verify": "name=editor.wordWrapColumn&&role=input setting-control-focus"
      },
      {
        "id": "word_wrap_column_selected",
        "desc": "The editor.wordWrapColumn input field is selected with its current value highlighted",
        "verify": "name=editor.wordWrapColumn&&role=input setting-control-focus"
      },
      {
        "id": "value_entered",
        "desc": "New word wrap column value has been typed into the input field",
        "verify": "name=editor.wordWrapColumn&&role=input setting-control-focus"
      },
      {
        "id": "setting_saved",
        "desc": "The editor.wordWrapColumn setting has been saved successfully",
        "verify": "task complete"
      }
    ],
    "transitions": [
      {
        "from": "vscode_settings_open",
        "to": "search_box_focused",
        "action": "click name=Settings - Visual Studio Code&&role=document-web"
      },
      {
        "from": "search_box_focused",
        "to": "search_results_shown",
        "action": "type \"word wrap column\""
      },
      {
        "from": "search_results_shown",
        "to": "word_wrap_column_selected",
        "action": "click name=editor.wordWrapColumn&&role=input setting-control-focus"
      },
      {
        "from": "word_wrap_column_selected",
        "to": "value_entered",
        "action": "type $word_wrap_column_value"
      },
      {
        "from": "value_entered",
        "to": "setting_saved",
        "action": "press Enter"
      }
    ]
  }
]
