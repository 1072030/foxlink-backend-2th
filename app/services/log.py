from app.core.database import Project  # 假设你的 Project 模型在 app.models 中

# 转换项目名称函数
async def convert_project_name(original_project_name):
    if original_project_name is not None:
        try:
            project_id = int(original_project_name)
            project = await Project.objects.filter(id=project_id).get_or_none()
            if project is not None:
                return project.name
            else:
                return project_id
        except ValueError:
            return 
    else:
        return 
    
