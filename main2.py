from nicegui import ui
from nsfw import NsfwNovelWriter

writer = NsfwNovelWriter()
state = writer.state

ui.markdown('# NSFW 小说生成器')
ui.markdown('请输入你的 NSFW 小说需求，点击生成后将展示小说的标题和概要。')

with ui.row().classes('w-full justify-center'):
    with ui.card().classes('w-2/3 min-w-[400px] max-w-[900px]'):
        requirements = ui.textarea('输入你的 NSFW 小说需求：').props('rows=6').classes('w-full').bind_value(state, 'requirements')
        def gen_overall():
            if state.requirements and state.requirements.strip():
                writer.design_overall(state.requirements)
                ui.notify('生成成功！', type='positive')
                render_characters()  # 角色直接由design_overall生成，刷新角色区
                render_chapters()    # 角色变动后章节需刷新
            else:
                ui.notify('请输入需求后再生成。', type='warning')
        with ui.row().classes('w-full justify-center'):
            ui.button('生成小说概要', on_click=gen_overall).classes('w-1/2')

# 小说概要、角色、章节等内容始终渲染，通过visible属性控制显示
with ui.row().classes('w-full justify-center'):
    card_novel = ui.card().classes('w-2/3 min-w-[400px] max-w-[900px]')
    card_novel.bind_visibility(state, 'title')
    with card_novel:
        ui.markdown('## 小说概要').classes('text-center')
        ui.input('小说标题：').classes('w-full').bind_value(state, 'title')
        ui.textarea('小说概要：').props('rows=4').classes('w-full').bind_value(state, 'overview')

        # --- 角色列表区域容器 ---
        character_container = ui.element()
        def render_characters():
            character_container.clear()
            with character_container:
                ui.markdown('## 角色列表').classes('text-center')
                # 使用表格展示角色
                columns = [
                    {'name': 'index', 'label': '序号', 'field': 'index', 'align': 'center'},
                    {'name': 'desc', 'label': '角色描述', 'field': 'desc', 'align': 'left'},
                    {'name': 'actions', 'label': '操作', 'field': 'actions', 'align': 'center'},
                ]
                rows = [
                    {'index': idx+1, 'desc': character, 'actions': idx}
                    for idx, character in enumerate(state.characters)
                ]
                def on_delete(idx):
                    state.characters.pop(idx)
                    render_characters()
                    render_chapters()
                def on_edit(idx):
                    edit_value = state.characters[idx]
                    edit_dialog = ui.dialog()
                    with edit_dialog:
                        edit_input = ui.input('编辑角色', value=edit_value).classes('w-full')
                        with ui.row().classes('justify-center'):
                            def save_edit():
                                state.characters[idx] = edit_input.value
                                edit_dialog.close()
                                render_characters()
                                render_chapters()
                            ui.button('保存', on_click=save_edit).props('color=primary')
                            ui.button('取消', on_click=edit_dialog.close)
                    edit_dialog.open()
                def cell_actions(row):
                    with ui.row().classes('gap-2 justify-center'):
                        ui.button('编辑', on_click=lambda idx=row['actions']: on_edit(idx)).props('size=sm')
                        ui.button('删除', on_click=lambda idx=row['actions']: on_delete(idx)).props('color=negative size=sm')
                def custom_row(row):
                    return [
                        ui.label(str(row['index'])),
                        ui.label(row['desc']),
                        cell_actions(row)
                    ]
                table = ui.table(columns=columns, rows=rows, row_key='index').classes('w-full')
                for tr, row in zip(table.rows, rows):
                    for i, cell in enumerate(custom_row(row)):
                        tr.clear_slot(i)
                        with tr.slot(i):
                            cell
                # 新增角色
                with ui.row().classes('gap-2 mt-2 justify-center'):
                    new_char = ui.input('新增角色').classes('w-2/3')
                    def add_char():
                        if new_char.value.strip():
                            state.characters.append(new_char.value.strip())
                            new_char.value = ''
                            render_characters()
                            render_chapters()
                    ui.button('添加角色', on_click=add_char).classes('w-1/3')
        render_characters()

        # --- 章节 tabs 区域容器 ---
        chapter_tabs_container = ui.element()
        def render_chapters():
            chapter_tabs_container.clear()
            with chapter_tabs_container:
                tabs_container = ui.row().classes('w-full justify-center')
                tabs_container.visible = bool(state.chapters)
                with tabs_container:
                    ui.markdown('## 章节概要').classes('text-center')
                    if state.chapters:
                        with ui.tabs().classes('w-full') as tabs:
                            tab_titles = [chapter.title or f'章节{i+1}' for i, chapter in enumerate(state.chapters)]
                            tab_objs = [ui.tab(title) for title in tab_titles]
                        with ui.tab_panels(tabs, value=tab_titles[0]).classes('w-full') as panels:
                            for idx, chapter in enumerate(state.chapters):
                                with ui.tab_panel(tab_titles[idx]):
                                    # 章节标题和概要可编辑
                                    ui.input(f'章节{idx+1}标题').classes('w-full mb-2').bind_value(chapter, 'title')
                                    ui.textarea(f'章节{idx+1}概要').classes('w-full mb-2').bind_value(chapter, 'overview')
                                    with ui.row().classes('justify-center'):
                                        btn_sec = ui.button('为本章节生成小节').classes('mb-2')
                                        btn_sec.on('click', lambda e, idx=idx, chapter=chapter, btn=btn_sec: update_sections(idx, chapter, btn_sec))
                                    # --- 小节列表区域容器 ---
                                    section_container = ui.element()
                                    def render_sections():
                                        section_container.clear()
                                        with section_container:
                                            if chapter.sections:
                                                ui.markdown('**小节列表： **').classes('text-center')
                                                for sidx, section in enumerate(chapter.sections):
                                                    with ui.row().classes('gap-2 flex-wrap justify-center'):
                                                        ui.input(f'章节{idx+1}小节{sidx+1}标题').classes('w-1/3 min-w-[180px]').bind_value(chapter.sections[sidx], 'title')
                                                        ui.textarea(f'章节{idx+1}小节{sidx+1}概要').classes('w-full').bind_value(chapter.sections[sidx], 'overview')
                                                    with ui.row().classes('gap-2 justify-center'):
                                                        btn_content = ui.button(f'生成章节{idx+1}小节{sidx+1}正文')
                                                        btn_content.on('click', lambda e, idx=idx, sidx=sidx, btn=btn_content: update_content(idx, sidx, btn_content))
                                    render_sections()
        render_chapters()

        # --- 生成按钮区域 ---
        with ui.row().classes('gap-4 justify-center'):
            # 移除角色列表生成按钮
            btn_chapters = ui.button('生成章节概要').classes('w-1/2')
            def update_chapters():
                if state.title and state.overview and state.language and state.characters:
                    btn_chapters.props('loading', True)
                    writer.design_chapters()
                    for chapter in state.chapters:
                        chapter.sections.clear()
                    ui.notify('章节概要生成成功！', type='positive')
                    render_chapters()
                    btn_chapters.props('loading', False)
                else:
                    ui.notify('请先生成小说概要后再生成章节概要。', type='warning')
            btn_chapters.on('click', update_chapters)

def update_sections(idx, chapter, btn=None):
        if btn:
            btn.props('loading', True)
        writer.design_sections(idx)
        ui.notify(f'已为{chapter.title or f"章节{idx+1}"}生成小节！', type='positive')
        render_chapters()
        if btn:
            btn.props('loading', False)
def update_content(idx, sidx, btn=None):
        if btn:
            btn.props('loading', True)
        writer.write_section_content(idx, sidx)
        ui.notify(f'已为章节{idx+1}小节{sidx+1}生成正文！', type='positive')
        render_chapters()
        if btn:
            btn.props('loading', False)

ui.run(title='NSFW Novel Generator', dark=True, reload=True, port=8080)