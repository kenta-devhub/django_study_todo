from rest_framework import serializers  # DRF（Django REST Framework）のシリアライザ基底クラス等を利用
from .models.task import Task  # 同アプリ内のTaskモデルを対象にする

class TaskSerializer(serializers.ModelSerializer):  # ModelインスタンスをJSON等へ自動変換するModelSerializer
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)  # 選択肢の表示名（priority）を文字列で出力（読み取り専用）
    status_label = serializers.CharField(source="get_status_display", read_only=True)  # 選択肢の表示名（status）を文字列で出力（読み取り専用）

    class Meta:  # シリアライザのメタ情報定義
        model = Task  # 対象モデルをTaskに指定
        fields = [  # APIで入出力するフィールド一覧（ここに載せた順でシリアライズ）
            "id", "title", "description", "due_date",  # 基本情報（due_dateはISO形式の'YYYY-MM-DD'で入出力）
            "priority", "priority_label",  # 数値の優先度と、その人間可読ラベル
            "completed", "status", "status_label",  # 完了フラグとKanban用状態、および各ラベル
            "created_at", "updated_at",  # 監査用の作成/更新日時（ISO 8601で出力、読み取り専用にするのが一般的）
        ]
        read_only_fields = ["id", "created_at", "updated_at"]  # クライアントからの書き込みを禁止するフィールド
