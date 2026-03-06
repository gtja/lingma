import pypandoc


def word_to_markdown(input_file, output_file):
    """
    将 Word 文档转换为 Markdown 文件。

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    try:
        output = pypandoc.convert_file(input_file, 'markdown', outputfile=output_file)
        if output == '':
            print(f"成功将 {input_file} 转换为 {output_file}")
            return True
        print(f"转换过程中出现异常输出: {output}")
        return False
    except Exception as e:
        print(f"转换失败: {e}")
        return False
