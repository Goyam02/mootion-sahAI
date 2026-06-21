import re
import sys

files = [
    "StudentAnalytics.tsx", "StudentPlaygroundPage.tsx", "StudentTaskActivityPage.tsx",
    "StudentTasksPage.tsx", "TeacherAnalytics.tsx", "TeacherAnalyticsPage.tsx",
    "TeacherChapterSetupPage.tsx", "TeacherClassViewPage.tsx", "TeacherDoubtsPage.tsx",
    "TeacherTopicSetupPage.tsx"
]

for f in files:
    path = f"frontend/src/pages/{f}"
    with open(path, "r") as file:
        content = file.read()
    
    # 1. Add LogoutModal import if not present
    if "LogoutModal" not in content:
        match = re.search(r"import .*? from 'react';", content)
        if match:
            original_import = match.group(0)
            if "useState" not in original_import:
                new_import = original_import.replace("import React", "import React, { useState }")
            else:
                new_import = original_import
            content = content.replace(original_import, new_import + "\nimport { LogoutModal } from '../components/LogoutModal';")
        else:
            content = "import { LogoutModal } from '../components/LogoutModal';\n" + content
    
    # 2. Add useState to component body
    component_name = f.split(".")[0]
    func_def = f"export function {component_name}() {{"
    if func_def in content and "isLogoutModalOpen" not in content:
        content = content.replace(func_def, f"{func_def}\n  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);")
    
    # 3. Replace api.logout() with setIsLogoutModalOpen(true)
    if "api.logout()" in content:
        content = content.replace("api.logout()", "setIsLogoutModalOpen(true)")
        
    # 4. Insert Modal at the end of the component
    if "Logout Confirmation" not in content:
        last_div_index = content.rfind("</div>")
        if last_div_index != -1:
            modal_code = "  {/* MODAL: Logout Confirmation */}\n      <LogoutModal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} />\n    "
            content = content[:last_div_index] + modal_code + content[last_div_index:]
    
    with open(path, "w") as file:
        file.write(content)

print("Refactoring complete.")
