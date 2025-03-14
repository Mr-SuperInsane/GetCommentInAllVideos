from googleapiclient.discovery import build
import time
import re

# YouTube Data APIのAPIキー
API_KEY = "YOUR_API_KEY"
YOUTUBE = build("youtube", "v3", developerKey=API_KEY)

# チャンネルID（変更する）
CHANNEL_ID = "UC****(YOUTUBE_CHANNEL_ID)"

# チャンネルIDの検索方法
'''
@のあとの「YOUTUBE_ID」にチャンネルを開いたときのURLの末尾(@以降)を指定して、YOUR_API_KEYにGCPのAPIを指定する
レスポンスの['items']['id']にチャンネルIDが含まれる
https://www.googleapis.com/youtube/v3/channels?part=id&forHandle=@YOUTUBE_ID&key=YOUR_API_KEY
'''

def get_all_videos(channel_id):
    """チャンネルの全動画IDを取得（Shortsを除外）"""
    video_ids = []
    next_page_token = None
    
    while True:
        response = YOUTUBE.search().list(
            part="id",
            channelId=channel_id,
            maxResults=50,
            order="date",
            type="video",
            pageToken=next_page_token
        ).execute()
        
        # 取得した動画IDをリストに追加
        batch_video_ids = [item["id"]["videoId"] for item in response.get("items", [])]

        # 動画の詳細情報を取得（まとめてAPIリクエストを減らす）
        video_details = YOUTUBE.videos().list(
            part="contentDetails,snippet",
            id=",".join(batch_video_ids)
        ).execute()

        for item in video_details.get("items", []):
            video_id = item["id"]
            title = item["snippet"]["title"]
            duration = item["contentDetails"]["duration"]

            # Shortsの除外（タイトルまたは動画時間が60秒以下）
            if "shorts" not in title.lower() and not is_short_video(duration):
                video_ids.append(video_id)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

        time.sleep(1)  # API制限回避

    return video_ids

def is_short_video(duration):
    """ISO 8601の動画時間を解析し、60秒以内ならTrueを返す"""
    match = re.search(r"PT(\d+H)?(\d+M)?(\d+S)?", duration)
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0
    return (hours * 3600 + minutes * 60 + seconds) <= 60

def get_comments(video_id):
    """特定の動画のすべてのコメントを取得（最大500件）"""
    comments = []
    next_page_token = None

    while True:
        try:
            response = YOUTUBE.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,  # 1リクエストで最大100件取得
                pageToken=next_page_token
            ).execute()

            for item in response.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment)

            next_page_token = response.get("nextPageToken")
            if not next_page_token or len(comments) >= 500:  # 500件制限
                break

        except Exception as e:
            print(f"⚠️ コメント取得エラー（動画ID: {video_id}）: {e}")
            break

        time.sleep(0.5)  # API制限回避

    return comments

def find_videos_with_keyword(channel_id, keyword):
    """指定した単語を含むコメントがある動画を抽出"""
    video_ids = get_all_videos(channel_id)
    result_videos = []

    print(f"🎥 チャンネル内の動画: {len(video_ids)} 件をチェック中...")

    for i, video_id in enumerate(video_ids, 1):
        print(f"🔍 {i}/{len(video_ids)}: {video_id} のコメントを取得中...", end="\r")
        comments = get_comments(video_id)

        # キーワード「ヒン」を含むコメントがあるか確認
        if any(keyword in comment for comment in comments):
            result_videos.append(video_id)
            print(f"✅ キーワード『{keyword}』を含む動画発見: https://www.youtube.com/watch?v={video_id}")

    return result_videos

if __name__ == "__main__":
    keyword = "ヒン"
    videos_with_keyword = find_videos_with_keyword(CHANNEL_ID, keyword)

    print("\n🔎 キーワード『ヒン』を含むコメントがある動画一覧:")
    for video_id in videos_with_keyword:
        print(f"https://www.youtube.com/watch?v={video_id}")
