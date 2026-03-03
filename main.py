"""
AI Companion 主应用入口
"""
import uvicorn
import argparse
from src.config.settings import settings

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI Companion - 智能陪伴机器人客服系统")
    parser.add_argument("--host", default=settings.host, help="主机地址")
    parser.add_argument("--port", type=int, default=settings.port, help="端口号")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")
    parser.add_argument("--log-level", default="info", help="日志级别")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    AI Companion - 智能陪伴机器人客服系统                    ║
║                                                              ║
║  版本: {settings.app_version:<49} ║
║  主机: {args.host:<49} ║
║  端口: {args.port:<49} ║
║  调试: {str(settings.debug):<49} ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 运行应用
    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()