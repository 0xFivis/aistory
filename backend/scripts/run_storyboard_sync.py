import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from app.database import get_db_session
from app.models.task import Task

try:
    from app.tasks.storyboard_task import generate_storyboard_task
except Exception as e:
    print('导入任务失败:', e)
    raise

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--task', type=int, required=True)
    args = p.parse_args()
    task_id = args.task
    print('同步执行 storyboard 任务，task_id=', task_id)
    try:
        # 使用 apply() 在当前进程同步执行 task（会返回结果或抛异常）
        res = generate_storyboard_task.apply(args=[task_id])
        print('任务执行完成，结果：', res)
        if hasattr(res, 'result'):
            print('result attr:', res.result)
    except Exception as e:
        print('任务执行异常：')
        import traceback
        traceback.print_exc()
    # 打印 DB 中任务状态和 scenes 简要
    db = get_db_session()
    try:
        task = db.get(Task, task_id)
        print('Task after run:', {'id': task.id, 'status': task.status, 'progress': task.progress, 'error_msg': task.error_msg})
        from app.models.media import Scene
        scenes = db.query(Scene).filter(Scene.task_id == task_id).all()
        print('Scene count:', len(scenes))
        for s in scenes:
            print(' scene', s.seq, s.narration_text[:80] if s.narration_text else None)
    finally:
        db.close()
