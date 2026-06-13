import win32com.client  # type: ignore

try:
    jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
    jvlink.JVInit("3UJC-3XNU-1KME-U68B-4")  # Wait, JVInit takes Software ID! I need the Software ID!
    # I can't run this directly unless I know the software ID!
except Exception as e:
    print(e)
