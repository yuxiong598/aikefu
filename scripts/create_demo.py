"""生成仅供本项目上传演示使用的 Word 测试样例。"""

from pathlib import Path

from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    output = ROOT / "examples" / "售后政策演示.docx"
    output.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    document.styles["Normal"].font.size = Pt(11)
    document.add_paragraph("售后政策演示", style="Title")
    document.add_paragraph("本文为毕业设计的虚构售后资料，用于验证知识入库、问答引用和工单流程。")
    document.add_paragraph("退货规则", style="Heading 1")
    document.add_paragraph("商品签收后七天内可以申请退货。申请时请提供订单编号，并保留商品原包装。")
    document.add_paragraph("退款跟进", style="Heading 1")
    document.add_paragraph("退货验收通过后，由客服核实退款进度。退款仍未到账时，可创建售后工单并附订单编号。")
    document.add_paragraph("物流查询", style="Heading 1")
    document.add_paragraph("订单发货后，可在订单详情页查看物流信息。物流长期没有更新时，可创建工单请求人工协助。")
    # 使用独占创建，避免覆盖用户已经编辑过的演示文件。
    with output.open("xb") as stream:
        document.save(stream)
    print(f"已生成演示样例 {output}")


if __name__ == "__main__":
    main()
