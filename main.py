import streamlit as st
import os
import json
from nsfw import NsfwNovelWriter
from domains import NSFWNovel

if not os.environ["OPENAI_API_KEY"]:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

st.title("NSFW 小说生成器")
st.markdown("""
请输入你的 NSFW 小说需求，点击生成后将展示小说的标题和概要。
""")

# 注入自适应高度的CSS
st.markdown("""
    <style>
    textarea[data-baseweb="textarea"] {
        min-height: 60px !important;
        max-height: 600px !important;
        height: auto !important;
        overflow-y: auto !important;
        resize: vertical !important;
    }
    </style>
""", unsafe_allow_html=True)

# 初始化/恢复 writer
if 'writer' not in st.session_state:
    st.session_state['writer'] = NsfwNovelWriter()
writer: NsfwNovelWriter = st.session_state['writer']
state = writer.state

# 需求输入
requirements = st.text_area(
    "输入你的 NSFW 小说需求：",
    height=150,
    value=state.requirements or "",
    key="requirements_input"
)
writer.state.requirements = requirements

# 生成按钮
if st.button("生成小说概要"):
    if requirements.strip():
        writer.design_overall(requirements)
        st.success("生成成功！")
    else:
        st.warning("请输入需求后再生成。")

# 重置按钮
if st.button("重置"):
    st.session_state['writer'] = NsfwNovelWriter()
    st.success("已重置所有内容！")
    st.rerun()

# 导出/导入state
col_export, col_import = st.columns(2)
with col_export:
    if st.button("导出为JSON"):
        st.download_button(
            label="下载JSON",
            data=json.dumps(state.model_dump(), ensure_ascii=False, indent=2),
            file_name=f"{state.title or 'NSFW小说'}.json",
            mime="application/json"
        )
with col_import:
    uploaded = st.file_uploader("从JSON导入", type=["json"], key="import_json_uploader")
    if uploaded is not None:
        try:
            data = json.load(uploaded)
            st.session_state['writer'] = NsfwNovelWriter()
            st.session_state['writer'].state = NSFWNovel.model_validate(data)
            st.success("导入成功！")
            # 清空file_uploader的session_state，防止无限rerun
            st.session_state.pop("import_json_uploader", None)
            
            st.rerun()
        except Exception as e:
            st.error(f"导入失败: {e}")

# 标题和概要编辑
if state.title is not None:
    # 导出markdown按钮（移动到概要之上，并同列）
    col_md1, col_md2 = st.columns(2)
    with col_md1:
        if st.button('生成导出文件'):
            writer.export_markdown()
            st.success('已生成导出文件！')
    with col_md2:
        if state.exported_markdown:
            st.download_button('下载导出Markdown', data=state.exported_markdown, file_name=f"{state.title or 'NSFW小说'}.md", mime='text/markdown')

    title = st.text_input("小说标题：", value=state.title or "", key="title_input")
    overall = st.text_area("小说概要：", value=state.overview or "", key="overview_input")
    state.title = title
    state.overview = overall
    st.subheader("角色列表：")
    # 编辑和删除
    new_characters = []
    for idx, character in enumerate(state.characters):
        col1, col2, col3 = st.columns([4, 8, 2])
        with col1:
            edited_name = st.text_input(f"角色名{idx+1}", value=character.name, key=f"character_name_{idx}")
        with col2:
            edited_desc = st.text_input(f"角色描述{idx+1}", value=character.description, key=f"character_desc_{idx}")
        with col3:
            remove = st.button("删除", key=f"remove_character_{idx}")
        if not remove:
            from domains import NSFWCharacter
            new_characters.append(NSFWCharacter(name=edited_name, description=edited_desc))
    # 增加角色（放到同一行）
    coln1, coln2, coln3 = st.columns([4, 8, 2])
    with coln1:
        new_char_name = st.text_input("新增角色名", value="", key="add_character_name")
    with coln2:
        new_char_desc = st.text_input("新增角色描述", value="", key="add_character_desc")
    with coln3:
        add_char_clicked = st.button("添加角色")
    if add_char_clicked and new_char_name.strip():
        from domains import NSFWCharacter
        new_characters.append(NSFWCharacter(name=new_char_name, description=new_char_desc))
    state.characters = new_characters

    # 角色列表直接由state.characters渲染，无需单独生成按钮
    def rerender():
        st.rerun()

    # 章生成按钮逻辑不变

    col_ch1, col_ch2 = st.columns([2,2])
    with col_ch1:
        chapter_count = st.selectbox("章数量", options=["AUTO"] + [str(i) for i in range(1, 21)], index=0, key="chapter_count")
    with col_ch2:
        if st.button('生成章概要'):
            if state.title and state.overview and state.language and state.characters:
                writer.design_chapters(chapter_count=None if chapter_count=="AUTO" else int(chapter_count))
                for chapter in state.chapters:
                    chapter.sections.clear()
                st.success('章概要生成成功！')
                rerender()
            else:
                st.warning('请先生成小说概要后再生成章概要。')

    # 章概要及其节编辑前，显示并可编辑各角色当前状态
    if state.current_state:
        st.markdown("### 角色当前状态")
        new_current_state = {}
        for char in state.characters:
            char_name = char.name
            char_state = state.current_state.get(char_name, "")
            new_state = st.text_area(f"{char_name} 当前状态", value=char_state, key=f"current_state_{char_name}")
            new_current_state[char_name] = new_state
        state.current_state = new_current_state

    # 展示章概要及其节编辑与生成
    if state.chapters:
        # 新增章按钮
        if st.button("新增章"):
            from domains import NSFWChapter
            state.chapters.append(NSFWChapter(title="", overview="", sections=[]))
            rerender()
        tab_titles = [chapter.title or f"章{idx+1}" for idx, chapter in enumerate(state.chapters)]
        tabs = st.tabs(tab_titles)
        chapters_to_delete = []
        for idx, (chapter, tab) in enumerate(zip(state.chapters, tabs)):
            with tab:
                # 删除本章按钮
                if st.button(f"删除本章", key=f"delete_chapter_{idx}"):
                    chapters_to_delete.append(idx)
                # 章标题和概要可编辑
                chapter_title = st.text_input(f"章{idx+1}标题", value=chapter.title or f"章{idx+1}", key=f"chapter_title_{idx}")
                chapter_overview = st.text_area(f"章{idx+1}概要", value=chapter.overview or "", key=f"chapter_overview_{idx}")
                chapter.title = chapter_title
                chapter.overview = chapter_overview
                # 节数量选择+生成节按钮同列
                col_sec1, col_sec2 = st.columns([2,2])
                with col_sec1:
                    section_count = st.selectbox(f"节数量", options=["AUTO"] + [str(i) for i in range(1, 21)], index=0, key=f"section_count_{idx}")
                with col_sec2:
                    if st.button(f"为本章生成节", key=f"gen_sections_{idx}"):
                        writer.design_sections(idx, section_count=None if section_count=="AUTO" else int(section_count))
                        st.success(f"已为{chapter_title}生成节！")
                # 展示并可编辑sections
                if chapter.sections:
                    st.markdown("**节列表：**")
                    sections_to_delete = []
                    for sidx, section in enumerate(chapter.sections):
                        col_secA, col_secB, col_secC = st.columns([4, 8, 2])
                        with col_secA:
                            sec_title = st.text_input(f"章{idx+1}节{sidx+1}标题", value=section.title or "", key=f"section_title_{idx}_{sidx}")
                        with col_secB:
                            sec_overview = st.text_area(f"章{idx+1}节{sidx+1}概要", value=section.overview or "", key=f"section_overview_{idx}_{sidx}")
                        with col_secC:
                            if st.button(f"删除本节", key=f"delete_section_{idx}_{sidx}"):
                                sections_to_delete.append(sidx)
                        # 生成正文按钮
                        if st.button(f"生成章{idx+1}节{sidx+1}正文", key=f"gen_content_{idx}_{sidx}"):
                            writer.write_section_content(idx, sidx)
                            st.success(f"已为章{idx+1}节{sidx+1}生成正文！")
                        # 写回state
                        section.title = sec_title
                        section.overview = sec_overview
                        # 正文内容自适应高度（仅当section.content不为None时显示）
                        if section.content is not None:
                            sec_content = st.text_area(
                                f"章{idx+1}节{sidx+1}内容",
                                value=section.content,
                                key=f"section_content_{idx}_{sidx}",
                                height=400  # 设置较大的默认高度
                            )
                            section.content = sec_content
                    # 实际删除节（倒序防止索引错位）
                    for sidx in sorted(sections_to_delete, reverse=True):
                        del chapter.sections[sidx]
                        rerender()
                # 新增节按钮
                if st.button(f"新增节", key=f"add_section_{idx}"):
                    from domains import NSFWSection
                    chapter.sections.append(NSFWSection(title="", overview="", content=None))
                    rerender()
        # 实际删除章（倒序防止索引错位）
        for idx in sorted(chapters_to_delete, reverse=True):
            del state.chapters[idx]
            rerender()

