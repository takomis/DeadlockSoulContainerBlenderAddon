# -*- coding: utf-8 -*-
"""Wording. The add-on is written in English and carries a Japanese dictionary.

Blender's own language decides which one shows (Preferences > Interface > Language).
`tr()` also falls back to the dictionary when the interface-translation switch is off
but Blender itself is running in Japanese, so the panel never ends up half-translated.

The Japanese uses Blender's own vocabulary — メッシュ / アーマチュア / ボーン / 頂点グループ /
ウェイト / マテリアル / テクスチャ / 原点 — instead of plain words invented for it
(2026-09-21, the user's call: "Blender の用語で説明してあげて"). Someone new to the add-on is
also new to Blender, and a private vocabulary only makes the manual harder to read.
"""
import bpy

JA = {
    # --- panel ---
    "Deadlock Soul Container": "Deadlock ソウルコンテナ",
    "1. Pick a mesh and press": "① メッシュオブジェクトを選択して実行",
    "2. Check it": "② チェック",
    "3. Build the mod": "③ mod をビルド",
    "Make it a soul container": "ソウルコンテナにする",
    "Summons joint1, binds it, matches the size and centres it.":
        "アーマチュアとボーン joint1 を追加し、頂点ウェイト 100% で割り当て、サイズと原点を合わせる。",
    "Selected: {name}": "選択中: {name}",
    "Nothing selected": "オブジェクト未選択",
    "Made: {name}": "作成済み: {name}",
    "The look can be set any time — it is kept when you press again.":
        "マテリアルはいつ設定してもよい（もう一度実行しても保持される）。",
    "Check": "チェック",
    "Build the mod": "mod をビルド",
    "Material (vmat)": "マテリアル（vmat）",
    "Settings": "設定",
    "One at a time:": "個別に実行:",
    "Export": "エクスポート",
    "Compile": "コンパイル",
    "Pack into vpk": "vpk にパック",
    "vpk": "vpk",
    "Base Color": "ベースカラー",
    "Normal": "ノーマル",
    "Roughness": "ラフネス",
    "none": "なし",

    # --- the material button ---
    "Set up the material": "マテリアルを設定",
    "Re-apply the picked images": "指定した画像を再適用",
    "Open an image file. It is wired into the material for you.":
        "画像ファイルを開くと、マテリアルへの接続まで自動で行う。",
    "Give the mesh a material with a Principled BSDF if it has none, and plug the "
    "images picked above into Base Color / Roughness / Normal":
        "マテリアルが無ければプリンシプル BSDF 付きで追加し、上で指定した画像を "
        "ベースカラー／ラフネス／ノーマルに接続する",
    "No material on this mesh — the button below adds one":
        "このメッシュにマテリアルが無い——下のボタンで追加できる",
    "Select one mesh object, then press": "メッシュオブジェクトを1つ選択してから実行",
    "added the material {name}": "マテリアル {name} を追加",
    "{socket} <- {img}": "{socket} ← {img}",
    "nothing to do (it already has a material)": "変更なし（マテリアルは設定済み）",
    "added a material (it had none)": "マテリアルが無かったので追加",

    # --- operator tooltips ---
    "Take the selected mesh and make it a soul container: copy it, summon the bone "
    "joint1, weigh every vertex to it, match the original's size and put its centre "
    "on the origin. Pressing it again keeps the copy you have been working on":
        "選択中のメッシュをソウルコンテナにする——複製し、ボーン joint1 を追加して全頂点に "
        "ウェイト 100% を割り当て、サイズガイドに合わせてスケールし、原点に移動する。"
        "もう一度実行しても、作業中の複製をそのまま使う",
    "Check the selected mesh against the soul container rules":
        "選択中のメッシュがソウルコンテナの条件を満たしているか調べる",
    "Export the selected mesh as FBX + vmat + vmdl into the CSDK 12 addon folder":
        "選択中のメッシュを FBX・vmat・vmdl として CSDK 12 のアドオンフォルダへエクスポートする",
    "Turn the vmdl and vmat into vmdl_c / vmat_c with the CSDK 12 resourcecompiler (Steam must be running)":
        "CSDK 12 の resourcecompiler で vmdl と vmat を vmdl_c / vmat_c にコンパイルする（Steam の起動が必要）",
    "Collect the compiled models/ into a vpk (the shape Deadlock Mod Manager takes)":
        "コンパイル済みの models/ を vpk にまとめる（Deadlock Mod Manager が読める形式）",
    "Export, compile and pack in one go. If it stops, it says why":
        "エクスポート → コンパイル → vpk パックを続けて実行する。止まった場合は理由を表示する",

    # --- messages from "make it a soul container" ---
    "{name} is a soul container now: {notes}": "{name} をソウルコンテナにした: {notes}",
    "copied {src} (the original is untouched)": "{src} を複製（元のオブジェクトは変更しない）",
    "this one is already ours — worked on it in place":
        "これはアドオンが作成したオブジェクト——そのまま処理した",
    "kept {name} and fixed it up (delete it to start over)":
        "作成済みの {name} をそのまま処理した（作り直すときは削除してから）",
    "applied the transforms": "トランスフォームを適用",
    "scaled {f}x to the size guide": "サイズガイドに合わせて {f} 倍にスケール",
    "moved the centre to the origin": "バウンディングボックスの中心を原点へ移動",
    "bound to {bone} at 100%": "{bone} に頂点ウェイト 100% を割り当て",
    "Select one mesh of your model, then press": "モデルのメッシュオブジェクトを1つ選択してから実行",

    # --- the check ---
    "Select one mesh, then press": "メッシュオブジェクトを1つ選択してから実行",
    "This is the size guide, not a model. Select a mesh of your own":
        "これはサイズガイド（参照用オブジェクト）。自分のメッシュを選択して",
    "Size: radius about {r} (original {ref})": "サイズ: 半径 約{r}（本家 {ref}）",
    "Size: radius about {r} — too far from the original {ref} (the unit is inch; built in metres?)":
        "サイズ: 半径 約{r}——本家 {ref} から離れすぎ（単位は inch。メートルで作られていない？）",
    "Centre is near the origin (off by {d})": "バウンディングボックスの中心が原点付近（ずれ {d}）",
    "Centre is {d} away from the origin — the hand position will be off":
        "中心が原点から {d} ずれている——ゲーム内で手の位置からずれる",
    "Location / rotation / scale are not applied (Ctrl+A > All Transforms)":
        "位置・回転・スケールが未適用（Ctrl+A → 全トランスフォーム）",
    "Not bound to a rig yet — {bone} at 100% is done for you when you build":
        "アーマチュアモディファイアーが無い——ビルド時に {bone} へウェイト 100% を割り当てる",
    "The bone {bone} is missing (the root must be {bone})": "ボーン {bone} が無い（ルートボーンは {bone}）",
    "{bone} is not the root (clear its parent)": "{bone} がルートボーンでない（親をクリアする）",
    "One bone: {bone}": "ボーンは {bone} の1本",
    "The soul container has only {bone}. Extra bones: {names}":
        "ソウルコンテナのボーンは {bone} のみ。余分なボーン: {names}",
    "No vertex group {bone} — it is made for you when you build":
        "頂点グループ {bone} が無い——ビルド時に作成する",
    "All {n} vertices weigh 100%": "全 {n} 頂点のウェイト合計が 100%",
    "{n} vertices are not at 100% — they are weighted for you when you build":
        "{n} 頂点のウェイト合計が 100% でない——ビルド時に割り当て直す",
    "One material ({name})": "マテリアル 1個（{name}）",
    "No material": "マテリアルが無い",
    "{n} materials — each one becomes a vmat": "マテリアル {n} 個——それぞれ vmat になる",
    "{n} materials — each one reads its own image":
        "マテリアル {n} 個——それぞれ自分のノードから画像を読む",
    "No colour texture on: {names} (the material's own colour is used)":
        "ベースカラーにテクスチャが無いマテリアル: {names}（マテリアルのベースカラーの色で出力する）",
    "Modifiers bring {raw} vertices down to {n} on export":
        "モディファイアーにより {raw} 頂点 → 書き出しでは {n} 頂点",
    "{n} vertices (original 29,964)": "頂点数 {n}（本家 29,964）",
    "{n} vertices — over the compiler's limit of {max}. Add a Decimate modifier (Ratio) to bring it down":
        "頂点数 {n}——コンパイラの上限 {max} を超えている。デシメートモディファイアー（比率）で減らす",
    "Check passed": "チェック 合格",
    "Check found something to fix (see the panel)": "チェック 要修正（パネルに一覧）",

    # --- export / compile / pack ---
    "The check has not passed. Fix it first": "チェックに通っていない。先に修正する",
    "CSDK 12 not found: {path} (fix it in the add-on preferences)":
        "CSDK 12 が見つからない: {path}（アドオンのプリファレンスで修正する）",
    "Set the CSDK 12 folder first: Edit > Preferences > Add-ons > Deadlock Soul Container":
        "先に CSDK 12 のフォルダを設定する: 編集 > プリファレンス > アドオン > Deadlock Soul Container",
    "The CSDK 12 folder is not set yet": "CSDK 12 のフォルダが未設定",
    "Edit > Preferences > Add-ons > Deadlock Soul Container":
        "編集 > プリファレンス > アドオン > Deadlock Soul Container",
    "The folder that holds game\\ and content\\ (Reduced_CSDK_12)":
        "game\\ と content\\ が入っているフォルダ（Reduced_CSDK_12）",
    "The mesh or the rig cannot be selected (hidden, or on another view layer)":
        "メッシュかアーマチュアを選択できない（非表示・別のビューレイヤー）",
    "Could not rename the materials for the export: {names}":
        "エクスポート用のマテリアル名に変更できなかった: {names}",
    "The mesh has no faces": "メッシュに面が無い",
    "Cleared {n} file(s) left by the last build": "前回のビルドの {n} ファイルを削除",
    "{name}: {w}x{h} -> {pw}x{ph} (Source needs powers of two)":
        "{name}: {w}x{h} → {pw}x{ph} にリサイズ（Source は2の累乗サイズが必要）",
    "Exported: {path}": "エクスポート完了: {path}",
    "Press \"Export\" first": "先に「エクスポート」を実行する",
    "resourcecompiler is missing: {path}": "resourcecompiler が無い: {path}",
    "The compiler did not run: {err}": "コンパイラを実行できなかった: {err}",
    "The compiler complains: {msg}": "コンパイラがエラーを返した: {msg}",
    "Compiled: {path}": "コンパイル完了: {path}",
    "No vmdl_c came out. See compile.log: {tail}": "vmdl_c が出力されなかった。compile.log を確認: {tail}",
    "Compile it first": "先に「コンパイル」を実行する",
    "Packed: {path} ({n} files)": "パック完了: {path}（{n} ファイル）",
    "Stopped at {step}: {err}": "{step}で停止: {err}",
    "Stopped at {step}": "{step}で停止",
    "export": "エクスポート",
    "compile": "コンパイル",
    "pack": "パック",
    "The mod is ready: {path}": "mod を出力した: {path}",

    # --- settings ---
    "CSDK 12 folder": "CSDK 12 のフォルダ",
    "The Reduced_CSDK_12 folder (it holds game and content)":
        "Reduced_CSDK_12 のフォルダ（中に game と content がある）",
    "Addon name": "アドオン名",
    "Written to content/citadel_addons/<this name>/. ASCII only":
        "content/citadel_addons/<この名前>/ に出力する。半角英数のみ",
    "Mod name": "mod 名",
    "The name of the vpk that comes out": "出力される vpk のファイル名",
    "vpk goes to": "vpk の出力先",
    "Include the rotation fix particles": "向き修正パーティクルを同梱",
    "Put the three particles that make the model follow the character (proven on cinna) into the vpk":
        "モデルがキャラクターの向きに追従するパーティクル3つ（cinna で実証済み）を vpk に含める",
    "Colour texture. Empty means the image plugged into Base Color is used":
        "カラーテクスチャ。空ならマテリアルのベースカラーに接続された画像を使う",
    "Normal map. Empty means the image behind the Normal Map node, or flat":
        "ノーマルマップ。空ならノーマルマップノードの画像、無ければフラット",
    "Roughness texture. Empty means the image plugged into Roughness, or a flat value":
        "ラフネステクスチャ。空ならラフネスに接続された画像、無ければ一定値",
    "Roughness (flat)": "ラフネス（一定値）",
    "Used when there is no roughness texture. 0 = smooth, 1 = rough":
        "ラフネステクスチャが無いときの値。0 = 滑らか、1 = 粗い",
    "Metallic": "メタリック",
    "Self-illumination": "自己発光",
    "0 is off. The base colour texture glows as it is":
        "0 で発光なし。ベースカラーのテクスチャがそのまま発光する",
    "Saturation": "彩度",
    "How strong the colours are in game. cinna used 1.25": "ゲーム内での彩度。cinna では 1.25",
}


def tr(text, **kw):
    """English in, the right language out. Keyword arguments fill {placeholders}."""
    out = bpy.app.translations.pgettext_iface(text)
    if out == text and bpy.app.translations.locale.startswith("ja"):
        out = JA.get(text, text)
    return out.format(**kw) if kw else out


def register():
    bpy.app.translations.register(__package__, {"ja_JP": {("*", k): v for k, v in JA.items()}})


def unregister():
    try:
        bpy.app.translations.unregister(__package__)
    except Exception:
        pass
